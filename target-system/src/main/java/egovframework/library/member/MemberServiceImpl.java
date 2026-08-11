package egovframework.library.member;

import java.util.List;
import java.util.UUID;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import egovframework.library.cmmn.exception.DataNotFoundException;

@Service("memberService")
public class MemberServiceImpl implements MemberService {

    @Autowired
    private MemberMapper memberMapper;

    @Override
    public List<MemberVO> selectMemberList(MemberSearchVO searchVO) {
        return memberMapper.selectMemberList(searchVO);
    }

    @Override
    public int selectMemberListCount(MemberSearchVO searchVO) {
        return memberMapper.selectMemberListCount(searchVO);
    }

    @Override
    public MemberVO selectMember(String memberId) {
        MemberVO memberVO = memberMapper.selectMember(memberId);
        if (memberVO == null) {
            throw new DataNotFoundException("회원을 찾을 수 없습니다. memberId=" + memberId);
        }
        return memberVO;
    }

    @Override
    @Transactional
    public void insertMember(MemberVO memberVO) {
        if (memberVO.getMemberId() == null || memberVO.getMemberId().isEmpty()) {
            memberVO.setMemberId("MB" + UUID.randomUUID().toString().substring(0, 8).toUpperCase());
        }
        if (memberVO.getMemberStatus() == null || memberVO.getMemberStatus().isEmpty()) {
            memberVO.setMemberStatus(MemberStatus.NORMAL.getCode());
        }
        memberMapper.insertMember(memberVO);
    }

    @Override
    @Transactional
    public void updateMember(MemberVO memberVO) {
        selectMember(memberVO.getMemberId());
        memberMapper.updateMember(memberVO);
    }

    @Override
    @Transactional
    public void deleteMember(String memberId) {
        selectMember(memberId);
        memberMapper.deleteMember(memberId);
    }
}
