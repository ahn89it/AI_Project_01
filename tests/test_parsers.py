"""analyzer.java_parser / analyzer.mapper_parser 스모크 + 검증 테스트.

target-system 실제 코드를 파싱해서 D4 완료 기준 6개 항목을 검증한다.
"""
import time
from pathlib import Path

import pytest

from analyzer import java_parser, mapper_parser
from server.config import JAVA_SRC_DIR, MAPPER_XML_DIR, TARGET_SYSTEM_DIR


@pytest.fixture(scope="module")
def parsed():
    start = time.time()
    classes, java_failed = java_parser.parse_directory(JAVA_SRC_DIR)
    sqls, mapper_failed = mapper_parser.parse_directory(MAPPER_XML_DIR)
    elapsed = time.time() - start
    return {
        "classes": classes,
        "java_failed": java_failed,
        "sqls": sqls,
        "mapper_failed": mapper_failed,
        "elapsed": elapsed,
    }


def test_1_controller_classification(parsed):
    """Controller 클래스가 4개 이상 검출되고 전부 CONTROLLER로 분류됨."""
    controllers = [c for c in parsed["classes"] if c.class_name.endswith("Controller")]
    assert len(controllers) >= 4, f"Controller 클래스가 4개 미만: {len(controllers)}"
    for c in controllers:
        assert c.layer == "CONTROLLER", f"{c.class_name}이 CONTROLLER로 분류되지 않음: {c.layer}"


def test_2_insert_loan_url_mapping(parsed):
    """/loan/insertLoan.do URL이 LoanController의 해당 메서드에 정확히 매핑됨."""
    loan_controller = next(c for c in parsed["classes"] if c.class_name == "LoanController")
    insert_methods = [m for m in loan_controller.methods if m.url == "/loan/insertLoan.do"]
    assert len(insert_methods) == 1, f"insertLoan.do 매핑된 메서드 개수 이상: {len(insert_methods)}"
    method = insert_methods[0]
    assert method.method_name == "insertLoan"
    assert "POST" in method.http_methods


def test_3_loan_service_impl_line_numbers(parsed):
    """LoanServiceImpl.insertLoan의 시작/끝 라인이 실제 파일과 일치.

    JSON 값과 실제 소스 파일을 둘 다 이 테스트 안에서 다시 읽어 직접 대조한다
    (파서 출력만 믿지 않고, 파일 원문에서 해당 라인의 텍스트가 기대한 모양인지 확인).
    """
    loan_service_impl = next(c for c in parsed["classes"] if c.class_name == "LoanServiceImpl")
    insert_loan = next(m for m in loan_service_impl.methods if m.method_name == "insertLoan")

    source_path = TARGET_SYSTEM_DIR / loan_service_impl.file_path
    lines = source_path.read_text(encoding="utf-8").splitlines()

    start_line_text = lines[insert_loan.start_line - 1]
    end_line_text = lines[insert_loan.end_line - 1]

    assert "@Override" in start_line_text or "insertLoan" in start_line_text, (
        f"시작 라인({insert_loan.start_line}) 내용이 예상과 다름: {start_line_text!r}"
    )
    assert end_line_text.strip() == "}", (
        f"끝 라인({insert_loan.end_line}) 내용이 예상과 다름: {end_line_text!r}"
    )
    # 메서드 본문 안에 실제 시그니처 라인이 범위 안에 있는지도 확인
    signature_lines = [
        i + 1 for i, l in enumerate(lines)
        if "public LoanResultVO insertLoan(LoanVO loanVO)" in l
    ]
    assert len(signature_lines) == 1
    assert insert_loan.start_line <= signature_lines[0] <= insert_loan.end_line


def test_4_insert_loan_sql_references_tb_loan(parsed):
    """Loan_SQL.xml의 insertLoan SQL에서 TB_LOAN 테이블이 추출됨."""
    insert_loan_sql = next(
        s for s in parsed["sqls"] if s.sql_id == "insertLoan" and "Loan_SQL.xml" in s.file_path
    )
    assert insert_loan_sql.sql_type == "insert"
    assert "TB_LOAN" in insert_loan_sql.referenced_tables


def test_5_overdue_join_query_four_tables(parsed):
    """연체자 목록 조회 SQL(4-테이블 JOIN)에서 참조 테이블 4개가 모두 추출됨."""
    overdue_list_sql = next(s for s in parsed["sqls"] if s.sql_id == "selectOverdueList")
    expected = {"TB_OVERDUE", "TB_LOAN", "TB_MEMBER", "TB_BOOK"}
    assert set(overdue_list_sql.referenced_tables) == expected, (
        f"참조 테이블 불일치: {overdue_list_sql.referenced_tables}"
    )


def test_6_performance_and_zero_failures(parsed):
    """전체 파싱 실행 시간 10초 이내, 실패 파일 0개."""
    assert parsed["elapsed"] < 10.0, f"파싱 시간 초과: {parsed['elapsed']:.2f}초"
    assert parsed["java_failed"] == [], f"Java 파싱 실패 파일: {parsed['java_failed']}"
    assert parsed["mapper_failed"] == [], f"Mapper 파싱 실패 파일: {parsed['mapper_failed']}"
