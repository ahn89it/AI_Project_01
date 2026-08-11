package egovframework.library.cmmn.vo;

import java.io.Serializable;

/**
 * API 공통 응답 래퍼. 주로 예외 발생 시 JSON 오류 응답을 표준화하는 데 사용한다.
 */
public class ResultVO implements Serializable {

    private static final long serialVersionUID = 1L;

    private boolean success;
    private String message;
    private Object data;

    public ResultVO() {
    }

    public ResultVO(boolean success, String message, Object data) {
        this.success = success;
        this.message = message;
        this.data = data;
    }

    public boolean isSuccess() {
        return success;
    }

    public void setSuccess(boolean success) {
        this.success = success;
    }

    public String getMessage() {
        return message;
    }

    public void setMessage(String message) {
        this.message = message;
    }

    public Object getData() {
        return data;
    }

    public void setData(Object data) {
        this.data = data;
    }
}
