package egovframework.library.loan;

import java.util.List;

import org.apache.ibatis.annotations.Param;

/**
 * 대출(TB_LOAN) / 대출이력(TB_LOAN_HIST) MyBatis 매퍼 인터페이스.
 * 실제 SQL은 resources/mappers/Loan_SQL.xml 참조.
 */
public interface LoanMapper {

    List<LoanVO> selectLoanList(LoanSearchVO searchVO);

    int selectLoanListCount(LoanSearchVO searchVO);

    LoanVO selectLoan(@Param("loanId") String loanId);

    /**
     * 특정 회원의 특정 상태 대출 건수 조회. 1인 최대 대출권수(5권) 검증에 사용.
     */
    int selectLoanCountByMember(@Param("memberId") String memberId, @Param("loanStatus") String loanStatus);

    void insertLoan(LoanVO loanVO);

    void updateReturn(LoanVO loanVO);

    void updateExtend(LoanVO loanVO);

    void insertLoanHist(LoanHistVO loanHistVO);
}
