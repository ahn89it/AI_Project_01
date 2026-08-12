"""Text-to-SQL 안전 검증기.

LLM이 생성한 SQL을 실행하기 전 마지막 방어선. sqlglot으로 구조를 파싱해서
SELECT 단일문인지, 존재하는 테이블만 쓰는지 확인하고 LIMIT을 강제한다.
이 검증을 통과해도 실제 실행은 ai_reader(SELECT 전용 DB 계정)로만 하므로 이중 방어가 된다.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Union

import sqlglot
from sqlglot import exp

from server.config import TEXT2SQL_MAX_ROW_LIMIT

_DIALECT = "mysql"

_FORBIDDEN_SUBSTRINGS = ("INTO OUTFILE", "INTO DUMPFILE", "LOAD_FILE", "/*!")


@dataclass
class ValidatedSql:
    sql: str
    notes: list = field(default_factory=list)  # LIMIT 추가 등 개입 내역


@dataclass
class GuardError:
    reason: str
    # False면 "고쳐서 다시 시도"가 무의미한 정책 위반(파괴적 SQL, 다중 문장 등)이라
    # text2sql.py가 재시도 없이 즉시 거부한다. True면 테이블명 오타/문법 실수처럼
    # 재생성으로 고칠 여지가 있다고 보고 1회 재시도한다.
    retryable: bool = True


def validate(sql: str, known_tables: set) -> Union[ValidatedSql, GuardError]:
    sql_upper = sql.upper()
    for forbidden in _FORBIDDEN_SUBSTRINGS:
        if forbidden in sql_upper:
            return GuardError(f"허용되지 않는 패턴이 포함되어 있습니다: {forbidden}", retryable=False)

    try:
        statements = [s for s in sqlglot.parse(sql, dialect=_DIALECT) if s is not None]
    except Exception as e:
        return GuardError(f"SQL 문법 오류: {e}", retryable=True)

    if len(statements) == 0:
        return GuardError("SQL이 비어 있습니다.", retryable=True)
    if len(statements) > 1:
        return GuardError("SELECT 단일 문장만 허용됩니다 (여러 SQL 문이 감지되었습니다).", retryable=False)

    stmt = statements[0]
    if not isinstance(stmt, exp.Select):
        return GuardError(f"SELECT문만 허용됩니다 (감지된 유형: {type(stmt).__name__}).", retryable=False)

    referenced_tables = {t.name.upper() for t in stmt.find_all(exp.Table)}
    unknown = referenced_tables - {t.upper() for t in known_tables}
    if unknown:
        return GuardError(f"존재하지 않는 테이블이 포함되어 있습니다: {', '.join(sorted(unknown))}", retryable=True)

    notes: list = []
    limit_node = stmt.args.get("limit")
    if limit_node is None:
        stmt.set("limit", exp.Limit(expression=exp.Literal.number(TEXT2SQL_MAX_ROW_LIMIT)))
        notes.append(f"LIMIT이 없어 자동으로 LIMIT {TEXT2SQL_MAX_ROW_LIMIT}을 추가했습니다.")
    else:
        try:
            limit_value = int(str(limit_node.expression.this))
            if limit_value > TEXT2SQL_MAX_ROW_LIMIT:
                stmt.set("limit", exp.Limit(expression=exp.Literal.number(TEXT2SQL_MAX_ROW_LIMIT)))
                notes.append(f"LIMIT {limit_value}을 최대 허용치 {TEXT2SQL_MAX_ROW_LIMIT}로 낮췄습니다.")
        except (TypeError, ValueError):
            stmt.set("limit", exp.Limit(expression=exp.Literal.number(TEXT2SQL_MAX_ROW_LIMIT)))
            notes.append(f"LIMIT 값을 해석할 수 없어 LIMIT {TEXT2SQL_MAX_ROW_LIMIT}으로 대체했습니다.")

    return ValidatedSql(sql=stmt.sql(dialect=_DIALECT), notes=notes)
