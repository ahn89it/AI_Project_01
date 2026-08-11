package egovframework.library.member;

import java.util.List;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Controller;
import org.springframework.ui.ModelMap;
import org.springframework.web.bind.annotation.ModelAttribute;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestMethod;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.ResponseBody;

import egovframework.library.cmmn.util.PagingUtil;
import egovframework.library.cmmn.vo.PaginationInfo;

@Controller
public class MemberController {

    @Autowired
    private MemberService memberService;

    @RequestMapping(value = "/member/selectMemberList.do", method = RequestMethod.GET)
    public String selectMemberList(@ModelAttribute MemberSearchVO searchVO, ModelMap model) {
        int totalCount = memberService.selectMemberListCount(searchVO);
        PaginationInfo paginationInfo = PagingUtil.calcPagination(totalCount, searchVO.getPageIndex(), searchVO.getPageSize());
        searchVO.setFirstIndex(paginationInfo.getFirstRecordIndex());

        List<MemberVO> resultList = memberService.selectMemberList(searchVO);

        model.addAttribute("resultList", resultList);
        model.addAttribute("paginationInfo", paginationInfo);
        model.addAttribute("searchVO", searchVO);
        return "member/memberList";
    }

    @RequestMapping(value = "/member/selectMemberDetail.do", method = RequestMethod.GET)
    @ResponseBody
    public MemberVO selectMemberDetail(@RequestParam("memberId") String memberId) {
        return memberService.selectMember(memberId);
    }

    @RequestMapping(value = "/member/insertMember.do", method = RequestMethod.POST)
    public String insertMember(@ModelAttribute MemberVO memberVO) {
        memberService.insertMember(memberVO);
        return "redirect:/member/selectMemberList.do";
    }

    @RequestMapping(value = "/member/updateMember.do", method = RequestMethod.POST)
    public String updateMember(@ModelAttribute MemberVO memberVO) {
        memberService.updateMember(memberVO);
        return "redirect:/member/selectMemberList.do";
    }

    @RequestMapping(value = "/member/deleteMember.do", method = RequestMethod.POST)
    public String deleteMember(@RequestParam("memberId") String memberId) {
        memberService.deleteMember(memberId);
        return "redirect:/member/selectMemberList.do";
    }
}
