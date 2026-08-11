"""DDL 스키마 카탈로그 파서.

target-system/db/schema.sql을 파싱해 테이블/컬럼/PK/FK/한글 코멘트를 추출하고
data/graph.db의 schema_catalog 테이블에 저장한다. Text-to-SQL(D9) 프롬프트에
그대로 넣을 수 있는 텍스트를 get_schema_text()로 제공한다.

sqlglot(dialect="mysql", MariaDB와 호환)으로 CREATE TABLE을 파싱한다.
COMMENT 추출이 sqlglot으로 실패하는 테이블이 있으면 정규식 보조로 재시도한다.

단독 실행:
    python -m analyzer.ddl_parser [schema.sql 경로]
    (경로 생략 시 server.config.DB_SCHEMA_SQL)
"""
from __future__ import annotations

import argparse
import logging
import re
import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import sqlglot
from sqlglot import exp

from server.config import DB_SCHEMA_SQL, GRAPH_DB_PATH

logger = logging.getLogger(__name__)

_DIALECT = "mysql"


@dataclass
class ColumnInfo:
    column_name: str
    data_type: str
    nullable: bool
    default_value: Optional[str]
    comment: Optional[str]
    is_pk: bool


@dataclass
class ForeignKeyInfo:
    column: str
    ref_table: str
    ref_column: str


@dataclass
class TableInfo:
    table_name: str
    table_comment: Optional[str]
    columns: list
    foreign_keys: list


def _literal_text(node) -> Optional[str]:
    if node is None:
        return None
    if isinstance(node, exp.Literal):
        return str(node.this)
    return node.sql(dialect=_DIALECT)


def _parse_create_table(stmt: exp.Create) -> TableInfo:
    schema_node = stmt.this
    table_name = schema_node.this.this.this  # Schema -> Table -> Identifier

    table_comment = None
    props = stmt.args.get("properties")
    if props is not None:
        for p in props.expressions:
            if isinstance(p, exp.SchemaCommentProperty):
                table_comment = _literal_text(p.this)

    pk_columns: set = set()
    fks: list = []
    for e in schema_node.expressions:
        if isinstance(e, exp.PrimaryKey):
            pk_columns.update(i.this for i in e.expressions)
        elif isinstance(e, exp.Constraint):
            for inner in e.expressions:
                if isinstance(inner, exp.ForeignKey):
                    local_cols = [c.this for c in inner.expressions]
                    ref = inner.args.get("reference")
                    if ref is not None:
                        ref_table = ref.this.this.this.this
                        ref_cols = [c.this for c in ref.this.expressions]
                        for lc, rc in zip(local_cols, ref_cols):
                            fks.append(ForeignKeyInfo(column=lc, ref_table=ref_table, ref_column=rc))

    columns: list = []
    for e in schema_node.expressions:
        if not isinstance(e, exp.ColumnDef):
            continue
        col_name = e.this.this
        data_type = e.args.get("kind").sql(dialect=_DIALECT) if e.args.get("kind") else ""

        nullable = True
        default_value = None
        comment = None
        for c in e.constraints or []:
            kind = c.kind
            if isinstance(kind, exp.NotNullColumnConstraint):
                nullable = False
            elif isinstance(kind, exp.PrimaryKeyColumnConstraint):
                nullable = False
                pk_columns.add(col_name)
            elif isinstance(kind, exp.DefaultColumnConstraint):
                default_value = _literal_text(kind.this)
            elif isinstance(kind, exp.CommentColumnConstraint):
                comment = _literal_text(kind.this)

        columns.append(ColumnInfo(
            column_name=col_name,
            data_type=data_type,
            nullable=nullable and col_name not in pk_columns,
            default_value=default_value,
            comment=comment,
            is_pk=col_name in pk_columns,
        ))

    return TableInfo(table_name=table_name, table_comment=table_comment, columns=columns, foreign_keys=fks)


_TABLE_BLOCK_RE = re.compile(
    r"CREATE TABLE\s+(\w+)\s*\((.*?)\)\s*(?:COMMENT\s*=?\s*'([^']*)')?\s*;",
    re.IGNORECASE | re.DOTALL,
)
_COLUMN_COMMENT_RE = re.compile(r"^\s*(\w+)\s+[\w()]+.*?COMMENT\s+'([^']*)'", re.IGNORECASE)


def _regex_fallback(table_name: str, full_sql: str) -> Optional[TableInfo]:
    """sqlglot으로 실패한 테이블에 대한 최소한의 정규식 보조 파싱 (테이블/컬럼 코멘트만)."""
    for m in _TABLE_BLOCK_RE.finditer(full_sql):
        if m.group(1).upper() != table_name.upper():
            continue
        body, table_comment = m.group(2), m.group(3)
        columns = []
        for line in body.split(","):
            cm = _COLUMN_COMMENT_RE.match(line)
            if cm:
                columns.append(ColumnInfo(
                    column_name=cm.group(1), data_type="", nullable=True,
                    default_value=None, comment=cm.group(2), is_pk=False,
                ))
        return TableInfo(table_name=table_name, table_comment=table_comment, columns=columns, foreign_keys=[])
    return None


def parse_schema(schema_path: Path) -> list:
    sql_text = schema_path.read_text(encoding="utf-8")
    statements = sqlglot.parse(sql_text, dialect=_DIALECT)

    tables: list = []
    for stmt in statements:
        if stmt is None or not isinstance(stmt, exp.Create) or stmt.args.get("kind") != "TABLE":
            continue
        table_name = "(unknown)"
        try:
            table_name = stmt.this.this.this.this
            tables.append(_parse_create_table(stmt))
        except Exception:
            logger.warning("sqlglot 파싱 실패, 정규식 보조로 재시도: %s", table_name, exc_info=True)
            fallback = _regex_fallback(table_name, sql_text)
            if fallback is not None:
                tables.append(fallback)
            else:
                logger.warning("정규식 보조도 실패, 건너뜀: %s", table_name)

    return tables


def create_schema_catalog_table(conn: sqlite3.Connection) -> None:
    conn.execute("DROP TABLE IF EXISTS schema_catalog")
    conn.execute("""
        CREATE TABLE schema_catalog (
            table_name TEXT NOT NULL,
            table_comment TEXT,
            column_name TEXT NOT NULL,
            data_type TEXT,
            nullable INTEGER,
            default_value TEXT,
            column_comment TEXT,
            is_pk INTEGER,
            fk_ref_table TEXT,
            fk_ref_column TEXT,
            PRIMARY KEY (table_name, column_name)
        )
    """)
    conn.execute("CREATE INDEX idx_schema_catalog_table ON schema_catalog(table_name)")


def store_schema_catalog(conn: sqlite3.Connection, tables: list) -> None:
    create_schema_catalog_table(conn)
    for t in tables:
        fk_by_col = {fk.column: fk for fk in t.foreign_keys}
        for c in t.columns:
            fk = fk_by_col.get(c.column_name)
            conn.execute(
                """INSERT INTO schema_catalog
                   (table_name, table_comment, column_name, data_type, nullable,
                    default_value, column_comment, is_pk, fk_ref_table, fk_ref_column)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    t.table_name, t.table_comment, c.column_name, c.data_type,
                    0 if not c.nullable else 1, c.default_value, c.comment,
                    1 if c.is_pk else 0,
                    fk.ref_table if fk else None,
                    fk.ref_column if fk else None,
                ),
            )
    conn.commit()


def get_schema_text(conn: sqlite3.Connection) -> str:
    """Text-to-SQL 프롬프트에 바로 넣을 수 있는 스키마 텍스트 (한글 코멘트 포함)."""
    rows = conn.execute("""
        SELECT table_name, table_comment, column_name, data_type, nullable,
               default_value, column_comment, is_pk, fk_ref_table, fk_ref_column
        FROM schema_catalog
        ORDER BY table_name, rowid
    """).fetchall()

    lines: list = []
    current_table = None
    for (table_name, table_comment, column_name, data_type, nullable,
         default_value, column_comment, is_pk, fk_ref_table, fk_ref_column) in rows:
        if table_name != current_table:
            if current_table is not None:
                lines.append("")
            header = f"TABLE {table_name}"
            if table_comment:
                header += f" -- {table_comment}"
            lines.append(header)
            current_table = table_name

        flags = []
        if is_pk:
            flags.append("PK")
        if not nullable:
            flags.append("NOT NULL")
        if default_value is not None:
            flags.append(f"DEFAULT {default_value}")
        if fk_ref_table:
            flags.append(f"FK -> {fk_ref_table}.{fk_ref_column}")
        flag_text = f" [{', '.join(flags)}]" if flags else ""

        comment_text = f"  -- {column_comment}" if column_comment else ""
        lines.append(f"  - {column_name} {data_type}{flag_text}{comment_text}")

    return "\n".join(lines)


def run(schema_path: Optional[str] = None, db_path: Optional[Path] = None) -> list:
    path = Path(schema_path) if schema_path else DB_SCHEMA_SQL
    if not path.exists():
        raise FileNotFoundError(f"schema.sql이 존재하지 않습니다: {path}")

    tables = parse_schema(path)

    target_db = db_path or GRAPH_DB_PATH
    target_db.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(target_db)
    try:
        store_schema_catalog(conn, tables)
    finally:
        conn.close()

    logger.info("schema_catalog 저장 완료: %s (테이블 %d개)", target_db, len(tables))
    return tables


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s - %(message)s")
    parser = argparse.ArgumentParser(description="DDL 스키마 카탈로그 추출")
    parser.add_argument("path", nargs="?", default=None, help="schema.sql 경로")
    args = parser.parse_args()

    try:
        run(args.path)
    except Exception:
        logger.error("ddl_parser 실행 실패", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
