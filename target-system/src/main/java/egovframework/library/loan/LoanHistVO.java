package egovframework.library.loan;

import java.io.Serializable;
import java.util.Date;

/**
 * 대출 처리 이력 VO (TB_LOAN_HIST 매핑). 대출/반납/연장마다 1건씩 적재되는 감사 로그.
 */
public class LoanHistVO implements Serializable {

    private static final long serialVersionUID = 1L;

    public static final String TYPE_LOAN = "1";   // 대출
    public static final String TYPE_RETURN = "2"; // 반납
    public static final String TYPE_EXTEND = "3"; // 연장

    private String histId;             // 이력ID
    private String loanId;             // 대출ID
    private String processType;        // 처리유형 (1=대출, 2=반납, 3=연장)
    private Date processDatetime;      // 처리일시
    private String processor;          // 처리자 (담당 사서ID 또는 SYSTEM)

    public String getHistId() {
        return histId;
    }

    public void setHistId(String histId) {
        this.histId = histId;
    }

    public String getLoanId() {
        return loanId;
    }

    public void setLoanId(String loanId) {
        this.loanId = loanId;
    }

    public String getProcessType() {
        return processType;
    }

    public void setProcessType(String processType) {
        this.processType = processType;
    }

    public Date getProcessDatetime() {
        return processDatetime;
    }

    public void setProcessDatetime(Date processDatetime) {
        this.processDatetime = processDatetime;
    }

    public String getProcessor() {
        return processor;
    }

    public void setProcessor(String processor) {
        this.processor = processor;
    }
}
