package egovframework.library.overdue;

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
public class OverdueController {

    @Autowired
    private OverdueService overdueService;

    /**
     * 연체자 목록. TB_OVERDUE + TB_LOAN + TB_MEMBER + TB_BOOK 조인 결과.
     */
    @RequestMapping(value = "/overdue/selectOverdueList.do", method = RequestMethod.GET)
    public String selectOverdueList(@ModelAttribute OverdueSearchVO searchVO, ModelMap model) {
        int totalCount = overdueService.selectOverdueListCount(searchVO);
        PaginationInfo paginationInfo = PagingUtil.calcPagination(totalCount, searchVO.getPageIndex(), searchVO.getPageSize());
        searchVO.setFirstIndex(paginationInfo.getFirstRecordIndex());

        List<OverdueVO> resultList = overdueService.selectOverdueList(searchVO);

        model.addAttribute("resultList", resultList);
        model.addAttribute("paginationInfo", paginationInfo);
        model.addAttribute("searchVO", searchVO);
        return "overdue/overdueList";
    }

    @RequestMapping(value = "/overdue/selectOverdueDetail.do", method = RequestMethod.GET)
    @ResponseBody
    public OverdueVO selectOverdueDetail(@RequestParam("overdueId") String overdueId) {
        return overdueService.selectOverdue(overdueId);
    }

    @RequestMapping(value = "/overdue/selectOverdueByMember.do", method = RequestMethod.GET)
    @ResponseBody
    public List<OverdueVO> selectOverdueByMember(@RequestParam("memberId") String memberId) {
        return overdueService.selectOverdueByMember(memberId);
    }

    @RequestMapping(value = "/overdue/updateRelease.do", method = RequestMethod.POST)
    public String updateRelease(@RequestParam("overdueId") String overdueId) {
        overdueService.updateRelease(overdueId);
        return "redirect:/overdue/selectOverdueList.do";
    }

    /**
     * 연체 상태 일괄 갱신 배치 트리거. 운영에서는 스케줄러가 호출하지만 데모에서는 화면 버튼으로 즉시 실행한다.
     */
    @RequestMapping(value = "/overdue/refreshOverdueStatus.do", method = RequestMethod.POST)
    @ResponseBody
    public String refreshOverdueStatus() {
        int updatedCount = overdueService.refreshOverdueStatus();
        return updatedCount + "건 갱신되었습니다.";
    }
}
