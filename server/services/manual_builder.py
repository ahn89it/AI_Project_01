"""업무 매뉴얼 자동 생성 엔진.

호출그래프(D5)의 URL 목록을 도메인별로 순회하며, 각 URL의 ServiceImpl 코드를 근거로
EXAONE이 처리 절차를 생성하고 하나의 Markdown 문서로 조립한다.
우선순위 최하 기능이므로 "완벽한 매뉴얼"이 아니라 "자동 생성되는 그럴듯한 매뉴얼"을
목표로 한다 — 과한 완성도를 추구하지 않는다.
"""
from __future__ import annotations

import json
import logging
import re
import sqlite3
from datetime import datetime
from typing import Callable, Optional

from analyzer.callgraph import get_chain, list_urls
from server.config import DATA_DIR, GRAPH_DB_PATH, TARGET_SYSTEM_DIR
from server.services.llm import chat
from server.services.prompts import MANUAL_SYSTEM_PROMPT, build_manual_user_prompt

logger = logging.getLogger(__name__)

MANUALS_DIR = DATA_DIR / "manuals"
CACHE_PATH = MANUALS_DIR / "_procedure_cache.json"

ProgressCallback = Callable[[int, int, str], None]

_DOMAIN_ORDER = ["book", "member", "loan", "overdue"]
_DOMAIN_KR = {"book": "도서 관리", "member": "회원 관리", "loan": "대출·반납", "overdue": "연체 관리"}

# 우리 시스템의 고정된 22개 URL에 대한 업무용 제목. 도메인이 4개뿐인 소규모 시스템이라
# LLM 호출 없이 표로 관리하는 편이 빠르고 안정적이다 (오늘의 "과욕 금지" 원칙).
_TITLE_OVERRIDES = {
    "selectBookList": "도서 목록 조회", "selectBookDetail": "도서 상세 조회",
    "selectCategoryList": "도서 분류 목록 조회", "insertBook": "도서 등록",
    "updateBook": "도서 정보 수정", "deleteBook": "도서 삭제",
    "selectMemberList": "회원 목록 조회", "selectMemberDetail": "회원 상세 조회",
    "insertMember": "회원 등록", "updateMember": "회원 정보 수정", "deleteMember": "회원 삭제",
    "selectLoanList": "대출 목록 조회", "selectLoanDetail": "대출 상세 조회",
    "checkLoanable": "대출 가능 여부 확인", "insertLoan": "도서 대출 등록",
    "updateReturn": "도서 반납 처리", "updateExtend": "대출 연장 처리",
    "selectOverdueList": "연체자 목록 조회", "selectOverdueDetail": "연체 상세 조회",
    "selectOverdueByMember": "회원별 연체 이력 조회", "updateRelease": "연체 해제 처리",
    "refreshOverdueStatus": "연체 상태 일괄 갱신",
}


def _load_cache() -> dict:
    if CACHE_PATH.exists():
        try:
            return json.loads(CACHE_PATH.read_text(encoding="utf-8"))
        except Exception:
            logger.warning("매뉴얼 캐시 로드 실패, 새로 시작합니다.", exc_info=True)
    return {}


def _save_cache(cache: dict) -> None:
    MANUALS_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")


def _read_lines(file_path: str, start_line: int, end_line: int) -> str:
    full_path = TARGET_SYSTEM_DIR / file_path
    lines = full_path.read_text(encoding="utf-8").splitlines()
    return "\n".join(lines[start_line - 1:end_line])


def _group_urls_by_domain(conn: sqlite3.Connection) -> dict:
    groups: dict = {}
    for u in list_urls(conn):
        domain = u["label"].strip("/").split("/")[0]
        groups.setdefault(domain, []).append(u)
    return groups


_LOGIC_KEYWORDS_RE = re.compile(r"\bif\s*\(|\bthrow\b")


def _is_trivial_delegate(impls: list) -> bool:
    """검증/조건문(if, throw)이 전혀 없는, 매퍼에 그대로 위임만 하는 메서드들인지 확인.

    이런 메서드는 실제 업무 로직이 없어서 LLM에 맡기면 설명할 내용이 없다보니
    "대출 금액", "대출 상품 유형" 같은(우리 도서관 시스템에는 없는, 은행 대출과 헷갈린)
    내용을 지어내는 경향이 관찰됐다 — "대출"이 책 대출과 금융 대출 양쪽에 다 쓰이는
    단어라 학습 데이터의 금융 도메인 쪽으로 끌려가는 것으로 보인다. 그래서 이런 경우는
    LLM을 아예 호출하지 않고 정형 문구로 대체한다.
    """
    for n in impls:
        code = _read_lines(n["file_path"], n["start_line"], n["end_line"])
        if _LOGIC_KEYWORDS_RE.search(code):
            return False
    return True


def _generate_procedure(url: str, impls: list, cache: dict) -> str:
    cached = cache.get(url)
    if cached:
        return cached["procedure"]

    if not impls:
        text = "- (관련 업무 로직 코드를 찾지 못했습니다.)"
        cache[url] = {"procedure": text, "generated_at": datetime.now().isoformat()}
        return text

    if _is_trivial_delegate(impls):
        text = (
            "1. 입력된 검색 조건에 맞는 데이터를 조회합니다.\n"
            "2. 조회된 결과를 반환합니다."
        )
        cache[url] = {"procedure": text, "generated_at": datetime.now().isoformat(), "trivial": True}
        return text

    blocks = []
    for n in impls:
        code = _read_lines(n["file_path"], n["start_line"], n["end_line"])
        header = f"[{n['file_path']}:{n['start_line']}-{n['end_line']}] {n['class_name']}.{n['method_name']}"
        comment = f"\n주석: {n['summary']}" if n.get("summary") else ""
        blocks.append(f"{header}{comment}\n{code}")
    context_text = "\n\n---\n\n".join(blocks)

    raw = chat(MANUAL_SYSTEM_PROMPT, build_manual_user_prompt(url, context_text), temperature=0.2)
    text = raw.strip()
    cache[url] = {"procedure": text, "generated_at": datetime.now().isoformat()}
    return text


def _build_entry(conn: sqlite3.Connection, url_node: dict, cache: dict) -> dict:
    chain = get_chain(conn, url_node["label"])
    nodes = chain["nodes"]

    controller = next((n for n in nodes if n["node_type"] == "CONTROLLER_METHOD"), None)
    impls = [n for n in nodes if n["node_type"] == "IMPL_METHOD"]
    tables = sorted({n["label"] for n in nodes if n["node_type"] == "TABLE"})
    sql_count = len([n for n in nodes if n["node_type"] == "SQL"])

    method_name = controller["method_name"] if controller else ""
    title = _TITLE_OVERRIDES.get(method_name, method_name or url_node["label"])

    chain_parts = []
    if controller:
        chain_parts.append(controller["label"])
    chain_parts.extend(sorted({n["label"] for n in impls}))
    chain_line = " → ".join(chain_parts) + (f" → SQL {sql_count}건" if sql_count else "")

    procedure = _generate_procedure(url_node["label"], impls, cache)

    return {
        "url": url_node["label"], "title": title, "procedure": procedure,
        "tables": tables, "chain_line": chain_line or "(호출그래프에서 찾지 못함)",
    }


def _build_overview(groups: dict, url_count: int, table_count: int) -> str:
    lines = ["## 1. 시스템 개요", "", f"자동 분석된 업무 도메인 (URL {url_count}개, 테이블 {table_count}개):", ""]
    for dom in _DOMAIN_ORDER:
        if dom in groups:
            lines.append(f"- **{_DOMAIN_KR[dom]}**: 기능 {len(groups[dom])}개")
    lines.append("")
    return "\n".join(lines)


def _build_appendix(conn: sqlite3.Connection) -> str:
    rows = conn.execute("""
        SELECT table_name, table_comment, column_name, data_type, nullable, is_pk, column_comment
        FROM schema_catalog ORDER BY table_name, rowid
    """).fetchall()

    lines = ["## 6. 부록: 테이블 정의서", ""]
    current = None
    for table_name, table_comment, column_name, data_type, nullable, is_pk, column_comment in rows:
        if table_name != current:
            if current is not None:
                lines.append("")
            header = f"### {table_name}"
            if table_comment:
                header += f" — {table_comment}"
            lines.append(header)
            lines.append("")
            lines.append("| 컬럼 | 타입 | PK | NULL 허용 | 설명 |")
            lines.append("|---|---|---|---|---|")
            current = table_name
        lines.append(f"| {column_name} | {data_type} | {'O' if is_pk else ''} | {'O' if nullable else 'X'} | {column_comment or ''} |")
    return "\n".join(lines)


def generate_manual(domain: str = "all", progress: Optional[ProgressCallback] = None) -> dict:
    generated_at = datetime.now().isoformat()

    conn = sqlite3.connect(GRAPH_DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        groups = _group_urls_by_domain(conn)

        if domain != "all":
            if domain not in groups:
                raise ValueError(f"알 수 없는 도메인입니다: {domain} (가능한 값: all, {', '.join(groups.keys())})")
            groups = {domain: groups[domain]}

        table_count = conn.execute("SELECT COUNT(DISTINCT table_name) FROM schema_catalog").fetchone()[0]
        total = sum(len(v) for v in groups.values())
        done = 0

        cache = _load_cache()
        domain_sections = []
        for dom in _DOMAIN_ORDER:
            if dom not in groups:
                continue
            entries = []
            for u in sorted(groups[dom], key=lambda x: x["label"]):
                entries.append(_build_entry(conn, u, cache))
                done += 1
                if progress:
                    progress(done, total, f"{_DOMAIN_KR[dom]}: {u['label']}")
                else:
                    logger.info("매뉴얼 생성 진행: %d/%d (%s)", done, total, u["label"])
            domain_sections.append((dom, entries))
        _save_cache(cache)

        overview = _build_overview(groups, total, table_count)
        appendix = _build_appendix(conn)
    finally:
        conn.close()

    parts = [
        "# 도서관 관리 시스템 업무 매뉴얼",
        "",
        f"- 생성일시: {generated_at}",
        "- 분석 대상: target-system/ (AI가 소스코드를 자동 분석해 작성한 문서입니다)",
        f"- 대상 URL 수: {total}개",
        "",
        overview,
    ]
    section_no = 2
    for dom, entries in domain_sections:
        parts.append(f"## {section_no}. {_DOMAIN_KR[dom]}")
        parts.append("")
        for e in entries:
            parts.append(f"### {e['title']}")
            parts.append(f"- 화면 경로: `{e['url']}`")
            parts.append("- 처리 절차:")
            parts.append(e["procedure"])
            parts.append(f"- 관련 테이블: {', '.join(e['tables']) if e['tables'] else '-'}")
            parts.append(f"- 참고: 처리 흐름 — {e['chain_line']}")
            parts.append("")
        section_no += 1
    parts.append(appendix)

    manual_md = "\n".join(parts)
    return {"manual_md": manual_md, "generated_at": generated_at, "url_count": total}
