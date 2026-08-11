package egovframework.library.book;

import java.util.List;

import javax.servlet.http.HttpServletRequest;

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
public class BookController {

    @Autowired
    private BookService bookService;

    /**
     * 도서 목록 조회. 서명/저자/분류/대출가능여부로 검색 가능.
     */
    @RequestMapping(value = "/book/selectBookList.do", method = RequestMethod.GET)
    public String selectBookList(@ModelAttribute BookSearchVO searchVO, ModelMap model) {
        int totalCount = bookService.selectBookListCount(searchVO);
        PaginationInfo paginationInfo = PagingUtil.calcPagination(totalCount, searchVO.getPageIndex(), searchVO.getPageSize());
        searchVO.setFirstIndex(paginationInfo.getFirstRecordIndex());

        List<BookVO> resultList = bookService.selectBookList(searchVO);

        model.addAttribute("resultList", resultList);
        model.addAttribute("paginationInfo", paginationInfo);
        model.addAttribute("searchVO", searchVO);
        return "book/bookList";
    }

    /**
     * 도서 상세 조회 (목록 화면에서 AJAX로 호출, JSON 응답)
     */
    @RequestMapping(value = "/book/selectBookDetail.do", method = RequestMethod.GET)
    @ResponseBody
    public BookVO selectBookDetail(@RequestParam("bookId") String bookId) {
        return bookService.selectBook(bookId);
    }

    /**
     * 도서 분류 목록 조회 (등록/수정 폼의 분류 콤보박스용, JSON 응답)
     */
    @RequestMapping(value = "/book/selectCategoryList.do", method = RequestMethod.GET)
    @ResponseBody
    public List<CategoryVO> selectCategoryList() {
        return bookService.selectCategoryList();
    }

    @RequestMapping(value = "/book/insertBook.do", method = RequestMethod.POST)
    public String insertBook(@ModelAttribute BookVO bookVO, HttpServletRequest request) {
        bookService.insertBook(bookVO);
        return "redirect:/book/selectBookList.do";
    }

    @RequestMapping(value = "/book/updateBook.do", method = RequestMethod.POST)
    public String updateBook(@ModelAttribute BookVO bookVO) {
        bookService.updateBook(bookVO);
        return "redirect:/book/selectBookList.do";
    }

    @RequestMapping(value = "/book/deleteBook.do", method = RequestMethod.POST)
    public String deleteBook(@RequestParam("bookId") String bookId) {
        bookService.deleteBook(bookId);
        return "redirect:/book/selectBookList.do";
    }
}
