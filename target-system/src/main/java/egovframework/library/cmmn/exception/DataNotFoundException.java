package egovframework.library.cmmn.exception;

/**
 * 조회 대상 데이터가 존재하지 않을 때 발생하는 예외.
 */
public class DataNotFoundException extends BusinessException {

    private static final long serialVersionUID = 1L;

    public DataNotFoundException(String message) {
        super("DATA_NOT_FOUND", message);
    }
}
