package egovframework.library.cmmn.util;

/**
 * 대출/연체 업무 규칙 상수.
 */
public final class LibraryConstants {

    /** 1인당 최대 동시 대출 가능 권수 */
    public static final int MAX_LOAN_COUNT = 5;

    /** 기본 대출 기간(일) */
    public static final int LOAN_PERIOD_DAYS = 14;

    /** 1회 연장 시 추가되는 기간(일) */
    public static final int EXTEND_PERIOD_DAYS = 7;

    private LibraryConstants() {
    }
}
