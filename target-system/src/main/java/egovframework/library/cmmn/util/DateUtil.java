package egovframework.library.cmmn.util;

import java.util.Calendar;
import java.util.Date;

/**
 * 대출/연체 관련 날짜 계산 유틸.
 */
public final class DateUtil {

    private DateUtil() {
    }

    /**
     * 반납예정일 계산. 대출일 + LOAN_PERIOD_DAYS(14일).
     */
    public static Date calcDueDate(Date loanDate) {
        return addDays(loanDate, LibraryConstants.LOAN_PERIOD_DAYS);
    }

    /**
     * 연장 후 반납예정일 계산. 기존 반납예정일 + EXTEND_PERIOD_DAYS(7일).
     */
    public static Date extendDueDate(Date dueDate) {
        return addDays(dueDate, LibraryConstants.EXTEND_PERIOD_DAYS);
    }

    /**
     * 연체일수 계산. baseDate가 dueDate를 지난 일수(음수가 나오지 않도록 0 이상으로 보정).
     */
    public static int calcOverdueDays(Date dueDate, Date baseDate) {
        long diffMillis = stripTime(baseDate).getTime() - stripTime(dueDate).getTime();
        long days = diffMillis / (1000L * 60 * 60 * 24);
        return days > 0 ? (int) days : 0;
    }

    public static Date addDays(Date date, int days) {
        Calendar cal = Calendar.getInstance();
        cal.setTime(date);
        cal.add(Calendar.DAY_OF_MONTH, days);
        return cal.getTime();
    }

    private static Date stripTime(Date date) {
        Calendar cal = Calendar.getInstance();
        cal.setTime(date);
        cal.set(Calendar.HOUR_OF_DAY, 0);
        cal.set(Calendar.MINUTE, 0);
        cal.set(Calendar.SECOND, 0);
        cal.set(Calendar.MILLISECOND, 0);
        return cal.getTime();
    }
}
