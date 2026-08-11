package egovframework.library.loan;

import egovframework.library.cmmn.exception.BusinessException;

/**
 * 대출 불가 사유가 있을 때 발생하는 예외.
 * errorCode: OVERDUE_MEMBER(연체중 회원) / LOAN_LIMIT_EXCEEDED(최대권수초과) / EXTEND_NOT_ALLOWED(연장불가) 등
 */
public class LoanNotAllowedException extends BusinessException {

    private static final long serialVersionUID = 1L;

    public LoanNotAllowedException(String errorCode, String message) {
        super(errorCode, message);
    }
}
