package egovframework.library.loan;

import egovframework.library.cmmn.vo.ComDefaultVO;

/**
 * 대출 목록 검색조건 VO
 */
public class LoanSearchVO extends ComDefaultVO {

    private static final long serialVersionUID = 1L;

    private String memberId;   // 회원ID 필터
    private String bookId;     // 도서ID 필터
    private String loanStatus; // 대출상태 필터

    public String getMemberId() {
        return memberId;
    }

    public void setMemberId(String memberId) {
        this.memberId = memberId;
    }

    public String getBookId() {
        return bookId;
    }

    public void setBookId(String bookId) {
        this.bookId = bookId;
    }

    public String getLoanStatus() {
        return loanStatus;
    }

    public void setLoanStatus(String loanStatus) {
        this.loanStatus = loanStatus;
    }
}
