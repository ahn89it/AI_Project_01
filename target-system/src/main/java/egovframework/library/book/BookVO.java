package egovframework.library.book;

import java.io.Serializable;
import java.util.Date;

/**
 * 도서 정보 VO (TB_BOOK 매핑)
 */
public class BookVO implements Serializable {

    private static final long serialVersionUID = 1L;

    private String bookId;         // 도서ID
    private String isbn;           // ISBN
    private String title;          // 서명
    private String author;         // 저자명
    private String publisher;      // 출판사명
    private Date publishDate;      // 출판일
    private String categoryCd;     // 분류코드
    private String categoryNm;     // 분류명 (조인 조회 시에만 채워짐)
    private String location;       // 소장위치
    private String loanYn;         // 대출가능여부 (Y/N)
    private Date regDate;          // 등록일시

    public String getBookId() {
        return bookId;
    }

    public void setBookId(String bookId) {
        this.bookId = bookId;
    }

    public String getIsbn() {
        return isbn;
    }

    public void setIsbn(String isbn) {
        this.isbn = isbn;
    }

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

    public String getPublisher() {
        return publisher;
    }

    public void setPublisher(String publisher) {
        this.publisher = publisher;
    }

    public Date getPublishDate() {
        return publishDate;
    }

    public void setPublishDate(Date publishDate) {
        this.publishDate = publishDate;
    }

    public String getCategoryCd() {
        return categoryCd;
    }

    public void setCategoryCd(String categoryCd) {
        this.categoryCd = categoryCd;
    }

    public String getCategoryNm() {
        return categoryNm;
    }

    public void setCategoryNm(String categoryNm) {
        this.categoryNm = categoryNm;
    }

    public String getLocation() {
        return location;
    }

    public void setLocation(String location) {
        this.location = location;
    }

    public String getLoanYn() {
        return loanYn;
    }

    public void setLoanYn(String loanYn) {
        this.loanYn = loanYn;
    }

    public Date getRegDate() {
        return regDate;
    }

    public void setRegDate(Date regDate) {
        this.regDate = regDate;
    }
}
