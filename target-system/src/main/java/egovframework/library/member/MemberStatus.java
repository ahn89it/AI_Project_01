package egovframework.library.member;

/**
 * 회원상태 코드 (TB_MEMBER.MEMBER_STATUS)
 */
public enum MemberStatus {

    NORMAL("1", "정상"),
    SUSPENDED("2", "대출정지"),
    WITHDRAWN("9", "탈퇴");

    private final String code;
    private final String label;

    MemberStatus(String code, String label) {
        this.code = code;
        this.label = label;
    }

    public String getCode() {
        return code;
    }

    public String getLabel() {
        return label;
    }

    public static MemberStatus fromCode(String code) {
        for (MemberStatus status : values()) {
            if (status.code.equals(code)) {
                return status;
            }
        }
        throw new IllegalArgumentException("알 수 없는 회원상태 코드입니다: " + code);
    }
}
