package egovframework.library.loan;

import java.io.Serializable;

/**
 * 대출 가능여부 사전 확인(checkLoanable) 및 대출 처리 결과를 화면에 전달하기 위한 VO.
 */
public class LoanResultVO implements Serializable {

    private static final long serialVersionUID = 1L;

    private boolean loanable;      // 처리 성공/가능 여부
    private String message;        // 사용자 안내 메시지
    private String failReasonCode; // 실패 사유 코드 (성공 시 null)

    public LoanResultVO() {
    }

    public LoanResultVO(boolean loanable, String message, String failReasonCode) {
        this.loanable = loanable;
        this.message = message;
        this.failReasonCode = failReasonCode;
    }

    public boolean isLoanable() {
        return loanable;
    }

    public void setLoanable(boolean loanable) {
        this.loanable = loanable;
    }

    public String getMessage() {
        return message;
    }

    public void setMessage(String message) {
        this.message = message;
    }

    public String getFailReasonCode() {
        return failReasonCode;
    }

    public void setFailReasonCode(String failReasonCode) {
        this.failReasonCode = failReasonCode;
    }
}
