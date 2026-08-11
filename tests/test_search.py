"""server.services.retriever.search() 한국어 검색 스모크 테스트.

analyzer.indexer로 실제 적재된 ChromaDB에 5개 업무 질의를 던져 top-5 결과를 검증한다.
목표: 5개 중 4개 이상 통과. + 각 결과의 node_id가 graph.db 노드와 실제로 조인되는지 확인.
"""
import sqlite3

import pytest

from server.config import GRAPH_DB_PATH
from server.services.retriever import search


@pytest.fixture(scope="module")
def graph_conn():
    conn = sqlite3.connect(GRAPH_DB_PATH)
    conn.row_factory = sqlite3.Row
    yield conn
    conn.close()


def _labels(hits):
    return [f"{h.metadata['class_name']}.{h.metadata['method_name']}" for h in hits]


def test_query_1_loan_process(graph_conn):
    """'도서 대출 처리 절차' → LoanServiceImpl.insertLoan이 top-5 안에."""
    hits = search("도서 대출 처리 절차", top_k=5)
    assert any(
        h.metadata["class_name"] == "LoanServiceImpl" and h.metadata["method_name"] == "insertLoan"
        for h in hits
    ), f"top-5: {_labels(hits)}"


def test_query_2_return_overdue(graph_conn):
    """'책 반납할 때 연체 처리' → updateReturn 관련 메서드가 top-5 안에."""
    hits = search("책 반납할 때 연체 처리", top_k=5)
    assert any(h.metadata["method_name"] == "updateReturn" for h in hits), f"top-5: {_labels(hits)}"


def test_query_3_overdue_member_list(graph_conn):
    """'연체 회원 목록 조회' → 연체 목록 SQL 또는 OverdueServiceImpl(계열)이 top-5 안에."""
    hits = search("연체 회원 목록 조회", top_k=5)
    assert any(
        "Overdue" in h.metadata["class_name"] and (
            h.metadata["method_name"] == "selectOverdueList" or h.metadata["layer"] != "SQL"
        )
        for h in hits
    ), f"top-5: {_labels(hits)}"


def test_query_4_max_loan_count(graph_conn):
    """'회원이 빌릴 수 있는 최대 권수' → 대출 한도 체크 메서드가 top-5 안에."""
    hits = search("회원이 빌릴 수 있는 최대 권수", top_k=5)
    assert any(
        h.metadata["method_name"] in ("checkLoanable", "insertLoan") and h.metadata["class_name"] == "LoanServiceImpl"
        for h in hits
    ), f"top-5: {_labels(hits)}"


def test_query_5_register_book(graph_conn):
    """'도서 등록은 어떻게 하나요' → BookController/BookServiceImpl의 insertBook이 top-5 안에."""
    hits = search("도서 등록은 어떻게 하나요", top_k=5)
    assert any(
        h.metadata["class_name"] in ("BookController", "BookServiceImpl") and h.metadata["method_name"] == "insertBook"
        for h in hits
    ), f"top-5: {_labels(hits)}"


@pytest.mark.parametrize("query", [
    "도서 대출 처리 절차",
    "책 반납할 때 연체 처리",
    "연체 회원 목록 조회",
    "회원이 빌릴 수 있는 최대 권수",
    "도서 등록은 어떻게 하나요",
])
def test_node_id_joins_to_graph_db(graph_conn, query):
    """검색 결과의 node_id가 전부 graph.db의 실제 노드와 조인되는지 확인 (RAG의 전제 조건)."""
    hits = search(query, top_k=5)
    assert len(hits) > 0
    for h in hits:
        row = graph_conn.execute("SELECT 1 FROM nodes WHERE id=?", (h.node_id,)).fetchone()
        assert row is not None, f"node_id '{h.node_id}'가 graph.db에 없음 (조인 키 불일치)"
