package egovframework.library.loan;

import java.util.List;

public interface LoanService {

    List<LoanVO> selectLoanList(LoanSearchVO searchVO);

    int selectLoanListCount(LoanSearchVO searchVO);

    LoanVO selectLoan(String loanId);

    /**
     * 대출 등록. 회원상태/최대권수/도서 대출가능여부를 검증한 뒤 TB_LOAN에 등록하고
     * 도서 상태 변경, 대출이력 기록까지 한 트랜잭션으로 처리한다.
     */
    LoanResultVO insertLoan(LoanVO loanVO);

    /**
     * 반납 처리. 반납예정일 초과 시 연체 등록 및 회원 대출정지 처리까지 수행한다.
     */
    void updateReturn(String loanId);

    /**
     * 대출 연장. 반납예정일을 7일 연장한다.
     */
    void updateExtend(String loanId);

    /**
     * 대출 등록 전 사전 확인(AJAX). 실제 등록 로직과 별개로 화면에서 안내 메시지를 보여주기 위함.
     */
    LoanResultVO checkLoanable(String memberId);
}
