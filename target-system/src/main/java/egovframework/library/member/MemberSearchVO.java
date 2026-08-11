package egovframework.library.member;

import egovframework.library.cmmn.vo.ComDefaultVO;

/**
 * 회원 목록 검색조건 VO
 */
public class MemberSearchVO extends ComDefaultVO {

    private static final long serialVersionUID = 1L;

    private String memberNm;     // 회원 이름 검색어 (부분일치)
    private String memberStatus; // 회원상태 필터

    public String getMemberNm() {
        return memberNm;
    }

    public void setMemberNm(String memberNm) {
        this.memberNm = memberNm;
    }

    public String getMemberStatus() {
        return memberStatus;
    }

    public void setMemberStatus(String memberStatus) {
        this.memberStatus = memberStatus;
    }
}
