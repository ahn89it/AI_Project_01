package egovframework.library.member;

import java.util.List;

public interface MemberService {

    List<MemberVO> selectMemberList(MemberSearchVO searchVO);

    int selectMemberListCount(MemberSearchVO searchVO);

    MemberVO selectMember(String memberId);

    void insertMember(MemberVO memberVO);

    void updateMember(MemberVO memberVO);

    void deleteMember(String memberId);
}
