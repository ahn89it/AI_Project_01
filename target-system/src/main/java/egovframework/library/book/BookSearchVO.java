package egovframework.library.book;

import egovframework.library.cmmn.vo.ComDefaultVO;

/**
 * 도서 목록 검색조건 VO. 페이징 정보는 ComDefaultVO에서 상속받는다.
 */
public class BookSearchVO extends ComDefaultVO {

    private static final long serialVersionUID = 1L;

    private String title;      // 서명 검색어 (부분일치)
    private String author;     // 저자 검색어 (부분일치)
    private String categoryCd; // 분류코드 필터
    private String loanYn;     // 대출가능여부 필터 (Y/N, 미지정 시 전체)

    public String getTitle() {
        return title;
    }

    public void setTitle(String title) {
        this.title = title;
    }

    public String getAuthor() {
        return author;
    }

    public void setAuthor(String author) {
        this.author = author;
    }

    public String getCategoryCd() {
        return categoryCd;
    }

    public void setCategoryCd(String categoryCd) {
        this.categoryCd = categoryCd;
    }

    public String getLoanYn() {
        return loanYn;
    }

    public void setLoanYn(String loanYn) {
        this.loanYn = loanYn;
    }
}
