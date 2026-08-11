package egovframework.library.cmmn.exception;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.ControllerAdvice;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.ResponseBody;

import egovframework.library.cmmn.vo.ResultVO;

/**
 * 컨트롤러 전역 예외 처리. 업무 예외는 400, 그 외 예상치 못한 예외는 500으로 매핑한다.
 */
@ControllerAdvice
public class GlobalExceptionHandler {

    private static final Logger LOGGER = LoggerFactory.getLogger(GlobalExceptionHandler.class);

    @ExceptionHandler(BusinessException.class)
    @ResponseBody
    public ResponseEntity<ResultVO> handleBusinessException(BusinessException ex) {
        LOGGER.warn("업무 예외 발생: errorCode={}, message={}", ex.getErrorCode(), ex.getMessage());
        return ResponseEntity.status(HttpStatus.BAD_REQUEST).body(new ResultVO(false, ex.getMessage(), ex.getErrorCode()));
    }

    @ExceptionHandler(Exception.class)
    @ResponseBody
    public ResponseEntity<ResultVO> handleException(Exception ex) {
        LOGGER.error("예상치 못한 오류 발생", ex);
        return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                .body(new ResultVO(false, "시스템 오류가 발생했습니다.", null));
    }
}
