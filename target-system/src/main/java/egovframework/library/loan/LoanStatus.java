package egovframework.library.loan;

/**
 * 대출상태 코드 (TB_LOAN.LOAN_STATUS)
 */
public enum LoanStatus {

    LOANED("1", "대출중"),
    RETURNED("2", "반납완료"),
    OVERDUE("3", "연체중");

    private final String code;
    private final String label;

    LoanStatus(String code, String label) {
        this.code = code;
        this.label = label;
    }

    public String getCode() {
        return code;
    }

    public String getLabel() {
        return label;
    }
}
