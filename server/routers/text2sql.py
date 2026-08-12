"""Text-to-SQL API. POST /api/text2sql

자연어 요청 → SQL 생성(EXAONE) → 안전 검증(sql_guard) → ai_reader로 실행 → 결과 반환.
검증 실패/실행 실패 시 실패 사유를 프롬프트에 덧붙여 1회만 재생성한다.
"""
from __future__ import annotations

import logging
import re
import sqlite3
import time
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

import pymysql
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from analyzer.ddl_parser import get_schema_text
from server.config import (
    GRAPH_DB_PATH,
    TARGET_DB_HOST,
    TARGET_DB_NAME,
    TARGET_DB_PASSWORD,
    TARGET_DB_PORT,
    TARGET_DB_QUERY_TIMEOUT_SEC,
    TARGET_DB_USER,
    TEXT2SQL_DEMO_TODAY,
)
from server.services.llm import OllamaConnectionError, chat
from server.services.prompts import TEXT2SQL_SYSTEM_PROMPT, build_text2sql_user_prompt
from server.services.sql_examples import select_examples
from server.services.sql_guard import GuardError, validate

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["text2sql"])

_CODE_BLOCK_RE = re.compile(r"```(?:sql)?\s*(.*?)```", re.IGNORECASE | re.DOTALL)
_SELECT_FALLBACK_RE = re.compile(r"(SELECT\b.*)", re.IGNORECASE | re.DOTALL)


class Text2SqlRequest(BaseModel):
    question: str


class Text2SqlResponse(BaseModel):
    sql: str
    columns: list
    rows: list
    row_count: int
    retried: bool
    guard_notes: list
    elapsed_ms: int


@dataclass
class _AttemptResult:
    sql: Optional[str]
    columns: Optional[list]
    rows: Optional[list]
    notes: Optional[list]  # None이면 guard 자체를 통과 못한 것 (검증 실패), 리스트면 검증은 통과
    error: Optional[str]
    retryable: bool = True  # False면 정책 위반(파괴적 SQL 등)이라 재시도 없이 즉시 거부


def _extract_sql(llm_output: str) -> Optional[str]:
    m = _CODE_BLOCK_RE.search(llm_output)
    if m:
        return m.group(1).strip()
    m = _SELECT_FALLBACK_RE.search(llm_output)
    if m:
        return m.group(1).strip()
    return None


def _serialize_cell(v):
    if isinstance(v, (bytes, bytearray)):
        return v.decode("utf-8", errors="replace")
    if isinstance(v, (datetime, date)):
        return v.isoformat()
    if isinstance(v, Decimal):
        return float(v)
    return v


def _execute_readonly(sql: str) -> tuple:
    conn = pymysql.connect(
        host=TARGET_DB_HOST, port=TARGET_DB_PORT, user=TARGET_DB_USER,
        password=TARGET_DB_PASSWORD, database=TARGET_DB_NAME,
        charset="utf8mb4", connect_timeout=10, read_timeout=TARGET_DB_QUERY_TIMEOUT_SEC + 5,
    )
    try:
        with conn.cursor() as cur:
            cur.execute(f"SET SESSION max_statement_time={TARGET_DB_QUERY_TIMEOUT_SEC}")
            cur.execute(sql)
            columns = [d[0] for d in cur.description] if cur.description else []
            rows = [[_serialize_cell(v) for v in row] for row in cur.fetchall()]
        return columns, rows
    finally:
        conn.close()


def _known_tables(conn: sqlite3.Connection) -> set:
    return {row[0] for row in conn.execute("SELECT DISTINCT table_name FROM schema_catalog")}


def _attempt(base_prompt: str, known_tables: set, failure_note: Optional[str]) -> _AttemptResult:
    prompt = base_prompt
    if failure_note:
        prompt += f"\n\n[이전 시도 문제]\n{failure_note}\n위 문제를 해결해서 SELECT SQL만 다시 생성하라."

    raw = chat(TEXT2SQL_SYSTEM_PROMPT, prompt, temperature=0.1)
    sql = _extract_sql(raw)
    if sql is None:
        return _AttemptResult(sql=None, columns=None, rows=None, notes=None,
                               error="SQL을 추출하지 못했습니다.", retryable=True)

    result = validate(sql, known_tables)
    if isinstance(result, GuardError):
        return _AttemptResult(sql=sql, columns=None, rows=None, notes=None,
                               error=result.reason, retryable=result.retryable)

    try:
        columns, rows = _execute_readonly(result.sql)
        return _AttemptResult(sql=result.sql, columns=columns, rows=rows, notes=result.notes, error=None)
    except Exception as e:
        logger.warning("SQL 실행 실패: %s", e)
        return _AttemptResult(sql=result.sql, columns=None, rows=None, notes=result.notes,
                               error=f"실행 오류: {e}", retryable=True)


@router.post("/text2sql", response_model=Text2SqlResponse)
def text2sql(req: Text2SqlRequest) -> Text2SqlResponse:
    start = time.time()

    conn = sqlite3.connect(GRAPH_DB_PATH)
    try:
        schema_text = get_schema_text(conn)
        known_tables = _known_tables(conn)
    finally:
        conn.close()

    examples = select_examples(req.question)
    base_prompt = build_text2sql_user_prompt(req.question, schema_text, TEXT2SQL_DEMO_TODAY, examples)

    try:
        result = _attempt(base_prompt, known_tables, failure_note=None)
        retried = False

        if result.error is not None and result.retryable:
            retried = True
            result = _attempt(base_prompt, known_tables, failure_note=result.error)
    except OllamaConnectionError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e

    elapsed_ms = int((time.time() - start) * 1000)

    if result.error is not None:
        if result.notes is not None:
            # 검증은 통과했지만(안전한 SELECT) 실행이 실패한 경우 — SQL과 에러를 함께 반환
            return Text2SqlResponse(
                sql=result.sql, columns=[], rows=[], row_count=0,
                retried=retried, guard_notes=result.notes + [result.error], elapsed_ms=elapsed_ms,
            )
        # 안전성 검증 자체를 통과하지 못함 (위험 쿼리/할루시네이션 테이블 등) — 명확히 거부
        raise HTTPException(status_code=400, detail=f"안전한 SELECT SQL을 생성하지 못했습니다: {result.error}")

    return Text2SqlResponse(
        sql=result.sql, columns=result.columns, rows=result.rows, row_count=len(result.rows),
        retried=retried, guard_notes=result.notes or [], elapsed_ms=elapsed_ms,
    )
