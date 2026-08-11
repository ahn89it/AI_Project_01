package egovframework.library.member;

import java.util.List;

import org.apache.ibatis.annotations.Param;

/**
 * 회원(TB_MEMBER) MyBatis 매퍼 인터페이스.
 * 실제 SQL은 resources/mappers/Member_SQL.xml 참조.
 */
public interface MemberMapper {

    List<MemberVO> selectMemberList(MemberSearchVO searchVO);

    int selectMemberListCount(MemberSearchVO searchVO);

    MemberVO selectMember(@Param("memberId") String memberId);

    void insertMember(MemberVO memberVO);

    void updateMember(MemberVO memberVO);

    void deleteMember(@Param("memberId") String memberId);

    /**
     * 회원상태 변경. 연체 제재/해제 처리 시 overdue 도메인에서 함께 호출한다.
     */
    void updateMemberStatus(@Param("memberId") String memberId, @Param("memberStatus") String memberStatus);
}
