package egovframework.library.book;

import java.util.List;
import java.util.UUID;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service("bookService")
public class BookServiceImpl implements BookService {

    @Autowired
    private BookMapper bookMapper;

    @Override
    public List<BookVO> selectBookList(BookSearchVO searchVO) {
        return bookMapper.selectBookList(searchVO);
    }

    @Override
    public int selectBookListCount(BookSearchVO searchVO) {
        return bookMapper.selectBookListCount(searchVO);
    }

    @Override
    public BookVO selectBook(String bookId) {
        BookVO bookVO = bookMapper.selectBook(bookId);
        if (bookVO == null) {
            throw new BookNotFoundException(bookId);
        }
        return bookVO;
    }

    @Override
    public List<CategoryVO> selectCategoryList() {
        return bookMapper.selectCategoryList();
    }

    @Override
    @Transactional
    public void insertBook(BookVO bookVO) {
        if (bookVO.getBookId() == null || bookVO.getBookId().isEmpty()) {
            bookVO.setBookId("BK" + UUID.randomUUID().toString().substring(0, 8).toUpperCase());
        }
        if (bookVO.getLoanYn() == null || bookVO.getLoanYn().isEmpty()) {
            bookVO.setLoanYn("Y");
        }
        bookMapper.insertBook(bookVO);
    }

    @Override
    @Transactional
    public void updateBook(BookVO bookVO) {
        // 등록 여부 확인 겸 존재하지 않는 도서 수정 시도를 사전에 차단
        selectBook(bookVO.getBookId());
        bookMapper.updateBook(bookVO);
    }

    @Override
    @Transactional
    public void deleteBook(String bookId) {
        selectBook(bookId);
        bookMapper.deleteBook(bookId);
    }
}
