package egovframework.library.overdue;

import java.io.Serializable;
import java.util.Date;

/**
 * 연체 정보 VO (TB_OVERDUE 매핑)
 */
public class OverdueVO implements Serializable {

    private static final long serialVersionUID = 1L;

    private String overdueId;         // 연체ID
    private String loanId;            // 대출ID
    private Date overdueStartDate;    // 연체시작일 (반납예정일 다음날)
    private int overdueDays;          // 연체일수
    private Date releaseDate;         // 연체해제일
    private String sanctionStatus;    // 제재상태 (1=제재중, 2=해제됨)

    // 목록 조회 시 조인으로 채워지는 표시용 필드 (TB_OVERDUE 컬럼 아님)
    private String memberId;          // 회원ID
    private String memberNm;          // 회원 이름
    private String bookTitle;         // 도서 서명

    public String getOverdueId() {
        return overdueId;
    }

    public void setOverdueId(String overdueId) {
        this.overdueId = overdueId;
    }

    public String getLoanId() {
        return loanId;
    }

    public void setLoanId(String loanId) {
        this.loanId = loanId;
    }

    public Date getOverdueStartDate() {
        return overdueStartDate;
    }

    public void setOverdueStartDate(Date overdueStartDate) {
        this.overdueStartDate = overdueStartDate;
    }

    public int getOverdueDays() {
        return overdueDays;
    }

    public void setOverdueDays(int overdueDays) {
        this.overdueDays = overdueDays;
    }

    public Date getReleaseDate() {
        return releaseDate;
    }

    public void setReleaseDate(Date releaseDate) {
        this.releaseDate = releaseDate;
    }

    public String getSanctionStatus() {
        return sanctionStatus;
    }

    public void setSanctionStatus(String sanctionStatus) {
        this.sanctionStatus = sanctionStatus;
    }

    public String getMemberId() {
        return memberId;
    }

    public void setMemberId(String memberId) {
        this.memberId = memberId;
    }

    public String getMemberNm() {
        return memberNm;
    }

    public void setMemberNm(String memberNm) {
        this.memberNm = memberNm;
    }

    public String getBookTitle() {
        return bookTitle;
    }

    public void setBookTitle(String bookTitle) {
        this.bookTitle = bookTitle;
    }
}
