package egovframework.library.loan;

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
public class LoanController {

    @Autowired
    private LoanService loanService;

    @RequestMapping(value = "/loan/selectLoanList.do", method = RequestMethod.GET)
    public String selectLoanList(@ModelAttribute LoanSearchVO searchVO, ModelMap model) {
        int totalCount = loanService.selectLoanListCount(searchVO);
        PaginationInfo paginationInfo = PagingUtil.calcPagination(totalCount, searchVO.getPageIndex(), searchVO.getPageSize());
        searchVO.setFirstIndex(paginationInfo.getFirstRecordIndex());

        List<LoanVO> resultList = loanService.selectLoanList(searchVO);

        model.addAttribute("resultList", resultList);
        model.addAttribute("paginationInfo", paginationInfo);
        model.addAttribute("searchVO", searchVO);
        return "loan/loanList";
    }

    @RequestMapping(value = "/loan/selectLoanDetail.do", method = RequestMethod.GET)
    @ResponseBody
    public LoanVO selectLoanDetail(@RequestParam("loanId") String loanId) {
        return loanService.selectLoan(loanId);
    }

    /**
     * 대출 등록 폼에서 신청 버튼을 누르기 전, 대출 가능 여부를 미리 확인하는 AJAX 엔드포인트.
     */
    @RequestMapping(value = "/loan/checkLoanable.do", method = RequestMethod.GET)
    @ResponseBody
    public LoanResultVO checkLoanable(@RequestParam("memberId") String memberId) {
        return loanService.checkLoanable(memberId);
    }

    @RequestMapping(value = "/loan/insertLoan.do", method = RequestMethod.POST)
    public String insertLoan(@ModelAttribute LoanVO loanVO) {
        loanService.insertLoan(loanVO);
        return "redirect:/loan/selectLoanList.do";
    }

    @RequestMapping(value = "/loan/updateReturn.do", method = RequestMethod.POST)
    public String updateReturn(@RequestParam("loanId") String loanId) {
        loanService.updateReturn(loanId);
        return "redirect:/loan/selectLoanList.do";
    }

    @RequestMapping(value = "/loan/updateExtend.do", method = RequestMethod.POST)
    public String updateExtend(@RequestParam("loanId") String loanId) {
        loanService.updateExtend(loanId);
        return "redirect:/loan/selectLoanList.do";
    }
}
