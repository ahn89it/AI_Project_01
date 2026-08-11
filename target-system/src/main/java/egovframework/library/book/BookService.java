package egovframework.library.book;

import java.util.List;

public interface BookService {

    List<BookVO> selectBookList(BookSearchVO searchVO);

    int selectBookListCount(BookSearchVO searchVO);

    BookVO selectBook(String bookId);

    List<CategoryVO> selectCategoryList();

    void insertBook(BookVO bookVO);

    void updateBook(BookVO bookVO);

    void deleteBook(String bookId);
}
