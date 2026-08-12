"""RAG 컨텍스트 조립: 벡터 검색 → 그래프 확장 → 코드 수집 → 토큰 예산 관리.

처리 순서 (D7 프롬프트 규약):
    a) retriever.search()로 진입점 청크 top-5 검색
    b) 상위 3개 히트의 node_id로 그래프 확장 (상류+하류 전체, callgraph.full_chain_for_node)
       → Controller 히트든 ServiceImpl 히트든 SQL 히트든, 어디가 걸리든
         "URL부터 테이블까지"의 완결된 흐름으로 확장된다
    c) 확장된 노드 중 실제 코드가 있는 것(Controller/ServiceImpl 메서드, SQL)만 코드 블록으로
       수집. 중복 제거, 체인 요약을 맨 앞에 둠
    d) 문자수 기준 토큰 예산(약 5000토큰 추정치) 내로 자르되, 우선순위를 지킨다:
       체인 요약 > 히트된 메서드 코드 > 하류(SQL 등) > 상류 코드 > 그 외 주변 코드
"""
from __future__ import annotations

import json
import logging
import re
import sqlite3
from dataclasses import dataclass
from typing import Optional

from analyzer.callgraph import downstream_subgraph, full_chain_for_node, upstream_subgraph
from server.config import GRAPH_DB_PATH, JAVA_SYMBOLS_JSON, TARGET_SYSTEM_DIR
from server.services.retriever import search

logger = logging.getLogger(__name__)

TOP_K_SEARCH = 5
TOP_N_EXPAND = 3

MAX_CONTEXT_TOKENS = 5000
CHARS_PER_TOKEN_ESTIMATE = 2  # 한글/코드 혼합 텍스트에 대한 넉넉한(보수적인) 추정치
MAX_CONTEXT_CHARS = MAX_CONTEXT_TOKENS * CHARS_PER_TOKEN_ESTIMATE

# 코드 블록을 실제로 보여줄 노드 유형 (SERVICE_METHOD/MAPPER_METHOD는 시그니처뿐이라 제외,
# URL/TABLE은 코드가 없음 — 체인 요약에서만 이름으로 언급)
_CODE_NODE_TYPES = {"CONTROLLER_METHOD", "IMPL_METHOD", "SQL"}
_LAYER_LABEL = {"CONTROLLER_METHOD": "Controller", "IMPL_METHOD": "ServiceImpl", "SQL": "SQL", "ETC_REF": "상수/코드정의"}

# 히트/체인 코드 안에서 "ClassName.CONSTANT"·"ClassName.ENUM_VALUE" 형태로 참조되는
# 업무 상수/enum(LibraryConstants, LoanStatus 등 ETC 계층)을 찾아내는 패턴.
# 이런 클래스는 그래프 노드가 아니라서(호출그래프 대상이 아님) 그냥 두면 실제 값(예: 최대
# 대출권수 5)이 컨텍스트에 전혀 안 잡혀 LLM이 "확인되지 않습니다"라고 답하게 된다.
_CONST_REF_RE = re.compile(r"\b([A-Z][A-Za-z0-9]*)\.[A-Z]")
_MAX_CONST_CLASS_LINES = 40  # 이보다 크면 유틸 클래스가 아니라고 보고 제외

_etc_classes_cache: Optional[dict] = None


def _get_etc_classes() -> dict:
    global _etc_classes_cache
    if _etc_classes_cache is None:
        classes = json.loads(JAVA_SYMBOLS_JSON.read_text(encoding="utf-8"))
        _etc_classes_cache = {c["class_name"]: c for c in classes if c["layer"] == "ETC"}
    return _etc_classes_cache


def _find_referenced_constant_classes(text: str) -> list:
    """text 안에서 참조된 ETC 계층(상수/enum 등) 클래스 중 작은 것만 골라 반환한다."""
    etc_classes = _get_etc_classes()
    names = {m.group(1) for m in _CONST_REF_RE.finditer(text)}
    found = []
    for name in sorted(names):
        c = etc_classes.get(name)
        if c is None:
            continue
        if c["end_line"] - c["start_line"] + 1 > _MAX_CONST_CLASS_LINES:
            continue
        found.append(c)
    return found

# 우선순위 tier (숫자가 작을수록 우선순위 높음). 1(체인 요약)은 항상 포함이라 여기 없음.
TIER_HIT = 2       # 히트된 메서드/SQL 코드 자체
TIER_DOWNSTREAM = 3  # 하류(호출하는 대상, SQL 등)
TIER_UPSTREAM = 4   # 상류(누가 호출하는지)
TIER_OTHER = 5      # 그 외 주변 코드


@dataclass
class Reference:
    file: str
    line_start: int
    line_end: int
    class_method: str
    snippet: str


@dataclass
class Context:
    text: str
    references: list
    chain_summary: str
    truncated: bool


def _read_source_lines(file_path: str, start_line: int, end_line: int) -> str:
    full_path = TARGET_SYSTEM_DIR / file_path
    lines = full_path.read_text(encoding="utf-8").splitlines()
    return "\n".join(lines[start_line - 1:end_line])


def _class_method_label(node: dict) -> str:
    if node["node_type"] == "ETC_REF":
        return node["class_name"]
    if node.get("class_name"):
        return f"{node['class_name']}.{node['method_name']}"
    # SQL 노드는 class_name이 비어있고 label이 "{namespace}.{sql_id}" 형태
    namespace_part, _, sql_id = node["label"].rpartition(".")
    mapper_class = namespace_part.rsplit(".", 1)[-1] if namespace_part else node["label"]
    return f"{mapper_class}.{sql_id}"


def _build_chain_summary(nodes: list) -> str:
    urls = sorted({n["label"] for n in nodes if n["node_type"] == "URL"})
    controllers = sorted({n["label"] for n in nodes if n["node_type"] == "CONTROLLER_METHOD"})
    impls = sorted({n["label"] for n in nodes if n["node_type"] == "IMPL_METHOD"})
    tables = sorted({n["label"] for n in nodes if n["node_type"] == "TABLE"})

    parts = [p for p in (" / ".join(urls), " / ".join(controllers), " / ".join(impls)) if p]
    chain = " → ".join(parts)
    if tables:
        chain = f"{chain} → 테이블({', '.join(tables)})" if chain else f"테이블({', '.join(tables)})"

    return f"처리 흐름: {chain}" if chain else "처리 흐름: 관련 코드를 찾지 못했습니다."


def _collect_candidate_nodes(hits: list, conn: sqlite3.Connection) -> dict:
    """상위 히트들을 그래프로 확장하고, 노드별로 가장 높은 우선순위(tier)를 매겨 반환한다.
    반환값: {node_id: (tier, node_dict)}"""
    candidates: dict = {}

    def consider(node: dict, tier: int) -> None:
        existing = candidates.get(node["id"])
        if existing is None or tier < existing[0]:
            candidates[node["id"]] = (tier, node)

    for hit in hits[:TOP_N_EXPAND]:
        sub = full_chain_for_node(conn, hit.node_id)
        node_by_id = {n["id"]: n for n in sub["nodes"]}

        hit_node = node_by_id.get(hit.node_id)
        if hit_node is not None:
            consider(hit_node, TIER_HIT)

        down_ids = {n["id"] for n in downstream_subgraph(conn, hit.node_id)["nodes"]}
        up_ids = {n["id"] for n in upstream_subgraph(conn, hit.node_id)["nodes"]}

        for nid, node in node_by_id.items():
            if nid == hit.node_id:
                continue
            if nid in down_ids:
                consider(node, TIER_DOWNSTREAM)
            elif nid in up_ids:
                consider(node, TIER_UPSTREAM)
            else:
                consider(node, TIER_OTHER)

    return candidates


def build_context(question: str) -> Context:
    hits = search(question, top_k=TOP_K_SEARCH)
    if not hits:
        return Context(
            text="처리 흐름: 관련 코드를 찾지 못했습니다.",
            references=[],
            chain_summary="처리 흐름: 관련 코드를 찾지 못했습니다.",
            truncated=False,
        )

    conn = sqlite3.connect(GRAPH_DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        candidates = _collect_candidate_nodes(hits, conn)
    finally:
        conn.close()

    all_nodes = [node for _, node in candidates.values()]
    chain_summary = _build_chain_summary(all_nodes)

    # 코드 블록 대상만 추려서 우선순위(tier) 순으로 정렬
    code_items = [
        (tier, node) for tier, node in candidates.values()
        if node["node_type"] in _CODE_NODE_TYPES
    ]

    # 히트된 메서드 코드(tier=TIER_HIT) 안에서 참조되는 업무 상수/enum(LibraryConstants,
    # LoanStatus 등)을 찾아 같은 우선순위로 끼워 넣는다 — 그래프 노드가 아니라 안 하면
    # "최대 대출권수" 같은 실제 값이 컨텍스트에서 통째로 빠진다.
    hit_text = "\n".join(
        _read_source_lines(node["file_path"], node["start_line"], node["end_line"])
        for tier, node in code_items if tier == TIER_HIT
    )
    seen_class_names = {node["class_name"] for _, node in code_items if node.get("class_name")}
    for c in _find_referenced_constant_classes(hit_text):
        if c["class_name"] in seen_class_names:
            continue
        seen_class_names.add(c["class_name"])
        code_items.append((TIER_HIT, {
            "id": f"ETC_REF::{c['class_name']}",
            "node_type": "ETC_REF",
            "class_name": c["class_name"],
            "method_name": None,
            "file_path": c["file_path"],
            "start_line": c["start_line"],
            "end_line": c["end_line"],
            "label": c["class_name"],
        }))

    code_items.sort(key=lambda t: (t[0], t[1]["file_path"] or "", t[1]["start_line"] or 0))

    blocks = [chain_summary]
    references: list = []
    used_chars = len(chain_summary)
    truncated = False

    for tier, node in code_items:
        try:
            code = _read_source_lines(node["file_path"], node["start_line"], node["end_line"])
        except Exception:
            logger.warning("소스 라인 읽기 실패, 건너뜀: %s", node["id"], exc_info=True)
            continue

        label = _class_method_label(node)
        header = f"[{node['file_path']}:{node['start_line']}-{node['end_line']}] {_LAYER_LABEL[node['node_type']]}/{label}"
        block = f"{header}\n{code}"

        if used_chars + len(block) > MAX_CONTEXT_CHARS:
            truncated = True
            logger.warning(
                "컨텍스트 문자수 예산(%d) 초과로 이후 블록 생략: %s (tier=%d)",
                MAX_CONTEXT_CHARS, node["id"], tier,
            )
            continue

        blocks.append(block)
        used_chars += len(block)
        references.append(Reference(
            file=node["file_path"],
            line_start=node["start_line"],
            line_end=node["end_line"],
            class_method=label,
            snippet=code.strip()[:200],
        ))

    context_text = "\n\n---\n\n".join(blocks)
    return Context(text=context_text, references=references, chain_summary=chain_summary, truncated=truncated)
