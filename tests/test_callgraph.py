"""analyzer.callgraph / analyzer.ddl_parser 검증 테스트.

D4 산출물(java_symbols.json, mapper_sqls.json)과 target-system/db/schema.sql로
실제 graph.db를 빌드해 D5 완료 기준 7개 항목을 검증한다.
"""
import re
import sqlite3

import pytest

from analyzer import callgraph
from analyzer.callgraph import expand, find_node_by_symbol, find_sqls_by_table, get_chain, list_urls
from analyzer.ddl_parser import get_schema_text
from server.config import GRAPH_DB_PATH, TARGET_SYSTEM_DIR


@pytest.fixture(scope="module")
def built():
    result = callgraph.run()
    conn = sqlite3.connect(GRAPH_DB_PATH)
    conn.row_factory = sqlite3.Row
    yield {"result": result, "conn": conn}
    conn.close()


def test_1_insert_loan_chain_covers_full_layer(built):
    """get_chain 결과에 Controller~Mapper~SQL~TB_LOAN이 모두 포함됨."""
    chain = get_chain(built["conn"], "/loan/insertLoan.do")
    assert chain["found"] is True

    class_names = {n["class_name"] for n in chain["nodes"] if n["class_name"]}
    assert "LoanController" in class_names
    assert "LoanService" in class_names        # 인터페이스
    assert "LoanServiceImpl" in class_names     # 구현체
    assert "LoanMapper" in class_names

    sql_ids = {n["method_name"] for n in chain["nodes"] if n["node_type"] == "SQL"}
    assert "insertLoan" in sql_ids

    tables = {n["label"] for n in chain["nodes"] if n["node_type"] == "TABLE"}
    assert "TB_LOAN" in tables


def test_2_insert_loan_chain_covers_multiple_tables(built):
    """insertLoan은 여러 SQL을 호출하므로 TB_BOOK, TB_LOAN_HIST도 잡히고 테이블이 3개 이상."""
    chain = get_chain(built["conn"], "/loan/insertLoan.do")
    tables = {n["label"] for n in chain["nodes"] if n["node_type"] == "TABLE"}
    assert "TB_BOOK" in tables
    assert "TB_LOAN_HIST" in tables
    assert len(tables) >= 3, f"테이블 참조가 3개 미만: {tables}"


def test_3_find_node_by_symbol_matches_source(built):
    """find_node_by_symbol이 정확한 파일:라인을 반환하고, 실제 파일과 대조해도 일치."""
    node = find_node_by_symbol(built["conn"], "LoanServiceImpl", "insertLoan")
    assert node is not None
    assert node["file_path"] == "src/main/java/egovframework/library/loan/LoanServiceImpl.java"
    assert node["start_line"] == 58
    assert node["end_line"] == 97

    # demo/error_log_1.txt 스택트레이스에 적힌 클래스.메서드로도 동일하게 조회되는지 확인
    error_log = (TARGET_SYSTEM_DIR / "demo" / "error_log_1.txt").read_text(encoding="utf-8")
    m = re.search(r"at egovframework\.library\.loan\.(\w+)\.(\w+)\(\w+\.java:(\d+)\)", error_log)
    assert m is not None, "error_log_1.txt에서 egovframework.library.loan.* 스택프레임을 못 찾음"
    log_class, log_method, log_line = m.group(1), m.group(2), int(m.group(3))

    node2 = find_node_by_symbol(built["conn"], log_class, log_method)
    assert node2 is not None, f"{log_class}.{log_method} 노드를 찾지 못함"
    assert node2["start_line"] <= log_line <= node2["end_line"], (
        f"에러로그 라인({log_line})이 노드 범위({node2['start_line']}~{node2['end_line']}) 밖"
    )


def test_4_overdue_table_has_multiple_sqls(built):
    """find_sqls_by_table('TB_OVERDUE')에 연체 관련 SQL이 2개 이상."""
    sqls = find_sqls_by_table(built["conn"], "TB_OVERDUE")
    assert len(sqls) >= 2, f"TB_OVERDUE 관련 SQL이 2개 미만: {[s['label'] for s in sqls]}"


def test_5_list_urls_matches_readme(built):
    """list_urls() 결과가 D2 README.md의 URL 목록과 완전히 일치."""
    graph_urls = {n["label"] for n in list_urls(built["conn"])}

    readme = (TARGET_SYSTEM_DIR / "README.md").read_text(encoding="utf-8")
    readme_urls = set(re.findall(r"/(?:book|member|loan|overdue)/\w+\.do", readme))

    assert graph_urls == readme_urls, (
        f"불일치 - README에만 있음: {readme_urls - graph_urls}, "
        f"그래프에만 있음: {graph_urls - readme_urls}"
    )


def test_6_schema_text_has_all_tables_and_korean_comments(built):
    """get_schema_text() 출력에 6개 테이블 + 한글 코멘트가 전부 포함됨."""
    text = get_schema_text(built["conn"])
    for table in ("TB_BOOK", "TB_MEMBER", "TB_LOAN", "TB_OVERDUE", "TB_CATEGORY", "TB_LOAN_HIST"):
        assert f"TABLE {table}" in text, f"{table}이 스키마 텍스트에 없음"

    korean_char_count = sum(1 for ch in text if "가" <= ch <= "힣")
    assert korean_char_count > 100, f"한글 코멘트가 부족해 보임 (한글 문자 수: {korean_char_count})"


def test_7_unresolved_ratio_under_10_percent(built):
    """연결 실패(unresolved) 비율이 10% 이하."""
    ratio = built["result"]["unresolved_ratio"]
    assert ratio <= 0.10, f"unresolved 비율 초과: {ratio:.1%}, 목록: {built['result']['unresolved']}"


def test_expand_returns_neighbors(built):
    """expand()가 지정한 노드의 상하류를 반환하는지 스모크 체크 (D7 RAG가 사용할 API)."""
    node_id = "IMPL_METHOD::LoanServiceImpl.insertLoan"
    result = expand(built["conn"], node_id, depth=1)
    neighbor_ids = {n["id"] for n in result["nodes"]}
    assert node_id in neighbor_ids
    assert len(result["nodes"]) > 1
