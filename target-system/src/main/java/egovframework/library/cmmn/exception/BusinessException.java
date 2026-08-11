package egovframework.library.cmmn.exception;

/**
 * 업무 규칙 위반 시 발생하는 공통 예외. errorCode로 실패 사유를 구분한다.
 */
public class BusinessException extends RuntimeException {

    private static final long serialVersionUID = 1L;

    private final String errorCode;

    public BusinessException(String errorCode, String message) {
        super(message);
        this.errorCode = errorCode;
    }

    public String getErrorCode() {
        return errorCode;
    }
}
