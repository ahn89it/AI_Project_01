"""Text-to-SQL few-shot 예시 선택기.

사용자 질문과 유사한 실제 Mapper XML SQL을 몇 개 골라 프롬프트에 예시로 넣는다.
이 예시가 이 시스템의 SQL 스타일(테이블명/조인 패턴/컬럼명)을 EXAONE이 따라하게 만드는
장치이므로, MyBatis 동적 태그(<if>, <where> 등)는 실행 불가능한 흔적을 남기지 않도록
정리한 뒤 넣는다.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Optional

from server.config import MAPPER_SQLS_JSON, TARGET_SYSTEM_DIR
from server.services.retriever import search

# 시연 질문이 연체 관련이고, 4-테이블 JOIN 패턴을 모델이 반드시 한 번은 봐야 정확히 흉내낸다.
# 검색 결과와 무관하게 예시 풀 최상단에 항상 포함시킨다.
_MANDATORY_MAPPER_CLASS = "OverdueMapper"
_MANDATORY_SQL_ID = "selectOverdueList"

_WHERE_BLOCK_RE = re.compile(r"<where>.*?</where>", re.IGNORECASE | re.DOTALL)
_IF_BLOCK_RE = re.compile(r"<if\b[^>]*>.*?</if>", re.IGNORECASE | re.DOTALL)
_OTHER_TAG_RE = re.compile(r"</?(?:foreach|choose|when|otherwise|set|trim)\b[^>]*>", re.IGNORECASE | re.DOTALL)
_LIMIT_PARAM_RE = re.compile(r"LIMIT\s+#\{[^}]+\}\s*,\s*#\{[^}]+\}", re.IGNORECASE)
_PARAM_RE = re.compile(r"#\{[^}]+\}")
_COMMENT_RE = re.compile(r"<!--\s*(.*?)\s*-->")

_SQL_TYPE_KR = {"select": "조회", "insert": "등록", "update": "수정", "delete": "삭제"}

_mapper_sqls_cache: Optional[list] = None


@dataclass
class SqlExample:
    purpose: str
    sql: str


# 실제 Mapper XML에는 없지만, 검증 중 "지금 대출 중인 책이 몇 권?" 질문에서 LLM이
# LOAN_STATUS='1'(대출중)만 세고 '3'(연체중)을 빠뜨려 절반만 세는 오류를 반복 관찰했다
# (연체중도 "아직 안 반납된" 대출이라 "대출 중"에 포함되어야 함). 스펙의 1차 대응책
# ("few-shot에 실패 유형과 유사한 예시를 수동으로 추가")에 따라 직접 작성해 항상 포함시킨다.
_MANUAL_EXAMPLES = [
    SqlExample(
        purpose="현재 대출 중(아직 반납 안 됨)인 도서 권수 — 대출중/연체중 모두 '반납 안 됨'이므로 "
                "LOAN_STATUS 값과 무관하게 RETURN_DATE가 비어있는 건을 센다",
        sql="SELECT COUNT(*) AS 대출중권수 FROM TB_LOAN WHERE RETURN_DATE IS NULL",
    ),
]


def _load_mapper_sqls() -> list:
    global _mapper_sqls_cache
    if _mapper_sqls_cache is None:
        _mapper_sqls_cache = json.loads(MAPPER_SQLS_JSON.read_text(encoding="utf-8"))
    return _mapper_sqls_cache


def _simplify_sql(sql_text: str) -> str:
    """MyBatis 동적 태그를 제거/단순화해 일반 SQL처럼 보이게 만든다."""
    text = _WHERE_BLOCK_RE.sub("", sql_text)
    text = _IF_BLOCK_RE.sub("", text)
    text = _OTHER_TAG_RE.sub("", text)
    text = _LIMIT_PARAM_RE.sub("LIMIT 10", text)
    text = _PARAM_RE.sub("'값'", text)
    lines = [line.rstrip() for line in text.splitlines() if line.strip()]
    return "\n".join(lines)


def _leading_comment(file_path: str, start_line: int) -> Optional[str]:
    """SQL 문 바로 위 줄의 XML 주석(있으면)을 용도 설명으로 재사용한다."""
    try:
        full_path = TARGET_SYSTEM_DIR / file_path
        lines = full_path.read_text(encoding="utf-8").splitlines()
        idx = start_line - 2  # 0-based, 문 바로 윗줄
        if idx < 0:
            return None
        m = _COMMENT_RE.match(lines[idx].strip())
        return m.group(1) if m else None
    except Exception:
        return None


def _purpose(info: dict) -> str:
    comment = _leading_comment(info["file_path"], info["start_line"])
    if comment:
        return comment
    mapper_class = info["namespace"].rsplit(".", 1)[-1]
    type_kr = _SQL_TYPE_KR.get(info["sql_type"], info["sql_type"])
    tables = ", ".join(info["referenced_tables"]) or "-"
    return f"{mapper_class}.{info['sql_id']} — {type_kr} (테이블: {tables})"


def select_examples(question: str, k: int = 5) -> list:
    mapper_sqls = _load_mapper_sqls()
    by_key = {(s["namespace"].rsplit(".", 1)[-1], s["sql_id"]): s for s in mapper_sqls}

    # 항상 포함(수동 예시 + 필수 JOIN 예시)이 예산을 다 차지하지 않도록 자리를 남겨둔다.
    reserved = min(1 + (1 if by_key.get((_MANDATORY_MAPPER_CLASS, _MANDATORY_SQL_ID)) else 0), k)
    remaining = max(k - reserved, 0)

    selected: list = []
    seen_keys: set = set()

    mandatory = by_key.get((_MANDATORY_MAPPER_CLASS, _MANDATORY_SQL_ID))
    if mandatory is not None:
        selected.append(mandatory)
        seen_keys.add((_MANDATORY_MAPPER_CLASS, _MANDATORY_SQL_ID))

    hits = search(question, top_k=remaining + 2, layer_filter="SQL")
    for h in hits:
        key = (h.metadata.get("class_name"), h.metadata.get("method_name"))
        if key in seen_keys:
            continue
        info = by_key.get(key)
        if info is None:
            continue
        seen_keys.add(key)
        selected.append(info)
        if len(selected) >= reserved + remaining:
            break

    examples = [SqlExample(purpose=_purpose(info), sql=_simplify_sql(info["sql_text"])) for info in selected]
    return _MANUAL_EXAMPLES + examples
