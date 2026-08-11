package egovframework.library.book;

import java.util.List;

import org.apache.ibatis.annotations.Param;

/**
 * 도서(TB_BOOK) / 분류(TB_CATEGORY) MyBatis 매퍼 인터페이스.
 * 실제 SQL은 resources/mappers/Book_SQL.xml 참조.
 */
public interface BookMapper {

    List<BookVO> selectBookList(BookSearchVO searchVO);

    int selectBookListCount(BookSearchVO searchVO);

    BookVO selectBook(@Param("bookId") String bookId);

    List<CategoryVO> selectCategoryList();

    void insertBook(BookVO bookVO);

    void updateBook(BookVO bookVO);

    void deleteBook(@Param("bookId") String bookId);

    /**
     * 도서 대출가능여부 변경. 대출 등록/반납 처리 시 loan 도메인에서 함께 호출한다.
     */
    void updateLoanYn(@Param("bookId") String bookId, @Param("loanYn") String loanYn);
}
