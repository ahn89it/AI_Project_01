package egovframework.library.overdue;

import egovframework.library.cmmn.vo.ComDefaultVO;

/**
 * 연체 목록 검색조건 VO
 */
public class OverdueSearchVO extends ComDefaultVO {

    private static final long serialVersionUID = 1L;

    private String memberId;       // 회원ID 필터
    private String sanctionStatus; // 제재상태 필터

    public String getMemberId() {
        return memberId;
    }

    public void setMemberId(String memberId) {
        this.memberId = memberId;
    }

    public String getSanctionStatus() {
        return sanctionStatus;
    }

    public void setSanctionStatus(String sanctionStatus) {
        this.sanctionStatus = sanctionStatus;
    }
}
