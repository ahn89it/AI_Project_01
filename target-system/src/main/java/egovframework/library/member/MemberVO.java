package egovframework.library.member;

import java.io.Serializable;
import java.util.Date;

/**
 * 회원 정보 VO (TB_MEMBER 매핑)
 */
public class MemberVO implements Serializable {

    private static final long serialVersionUID = 1L;

    private String memberId;      // 회원ID
    private String memberNm;      // 회원 이름
    private Date birthDate;       // 생년월일
    private String phone;         // 연락처
    private String email;         // 이메일
    private String memberStatus;  // 회원상태 (1=정상, 2=대출정지, 9=탈퇴)
    private Date joinDate;        // 가입일

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

    public Date getBirthDate() {
        return birthDate;
    }

    public void setBirthDate(Date birthDate) {
        this.birthDate = birthDate;
    }

    public String getPhone() {
        return phone;
    }

    public void setPhone(String phone) {
        this.phone = phone;
    }

    public String getEmail() {
        return email;
    }

    public void setEmail(String email) {
        this.email = email;
    }

    public String getMemberStatus() {
        return memberStatus;
    }

    public void setMemberStatus(String memberStatus) {
        this.memberStatus = memberStatus;
    }

    public Date getJoinDate() {
        return joinDate;
    }

    public void setJoinDate(Date joinDate) {
        this.joinDate = joinDate;
    }
}
