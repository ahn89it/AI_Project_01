package egovframework.library.overdue;

/**
 * 제재상태 코드 (TB_OVERDUE.SANCTION_STATUS)
 */
public enum OverdueStatus {

    SANCTIONED("1", "제재중"),
    RELEASED("2", "해제됨");

    private final String code;
    private final String label;

    OverdueStatus(String code, String label) {
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
