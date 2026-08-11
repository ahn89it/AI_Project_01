package egovframework.library.book;

import egovframework.library.cmmn.exception.BusinessException;

/**
 * 존재하지 않는 도서ID로 조회/대출을 시도한 경우 발생하는 예외.
 */
public class BookNotFoundException extends BusinessException {

    private static final long serialVersionUID = 1L;

    public BookNotFoundException(String bookId) {
        super("BOOK_NOT_FOUND", "도서를 찾을 수 없습니다. bookId=" + bookId);
    }
}
