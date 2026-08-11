package egovframework.library.loan;

import java.io.Serializable;
import java.util.Date;

/**
 * 대출 정보 VO (TB_LOAN 매핑)
 */
public class LoanVO implements Serializable {

    private static final long serialVersionUID = 1L;

    private String loanId;      // 대출ID
    private String bookId;      // 도서ID
    private String memberId;    // 회원ID
    private Date loanDate;      // 대출일
    private Date dueDate;       // 반납예정일
    private Date returnDate;    // 실제반납일
    private String loanStatus;  // 대출상태 (1=대출중, 2=반납완료, 3=연체중)
    private int extendCnt;      // 연장횟수

    // 목록/상세 조회 시 조인으로 채워지는 표시용 필드 (TB_LOAN 컬럼 아님)
    private String bookTitle;   // 도서 서명
    private String memberNm;    // 회원 이름

    public String getLoanId() {
        return loanId;
    }

    public void setLoanId(String loanId) {
        this.loanId = loanId;
    }

    public String getBookId() {
        return bookId;
    }

    public void setBookId(String bookId) {
        this.bookId = bookId;
    }

    public String getMemberId() {
        return memberId;
    }

    public void setMemberId(String memberId) {
        this.memberId = memberId;
    }

    public Date getLoanDate() {
        return loanDate;
    }

    public void setLoanDate(Date loanDate) {
        this.loanDate = loanDate;
    }

    public Date getDueDate() {
        return dueDate;
    }

    public void setDueDate(Date dueDate) {
        this.dueDate = dueDate;
    }

    public Date getReturnDate() {
        return returnDate;
    }

    public void setReturnDate(Date returnDate) {
        this.returnDate = returnDate;
    }

    public String getLoanStatus() {
        return loanStatus;
    }

    public void setLoanStatus(String loanStatus) {
        this.loanStatus = loanStatus;
    }

    public int getExtendCnt() {
        return extendCnt;
    }

    public void setExtendCnt(int extendCnt) {
        this.extendCnt = extendCnt;
    }

    public String getBookTitle() {
        return bookTitle;
    }

    public void setBookTitle(String bookTitle) {
        this.bookTitle = bookTitle;
    }

    public String getMemberNm() {
        return memberNm;
    }

    public void setMemberNm(String memberNm) {
        this.memberNm = memberNm;
    }
}
