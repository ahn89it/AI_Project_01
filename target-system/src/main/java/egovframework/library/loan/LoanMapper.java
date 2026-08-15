package egovframework.library.loan;

import java.util.List;

import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

/**
 * 대출(TB_LOAN) / 대출이력(TB_LOAN_HIST) MyBatis 매퍼 인터페이스.
 * 실제 SQL은 resources/mappers/Loan_SQL.xml 참조.
 */
@Mapper
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

    /**
     * 대출상태만 별도로 변경. 연체 상태 일괄 갱신 배치(overdue 도메인)에서 사용.
     */
    void updateLoanStatus(@Param("loanId") String loanId, @Param("loanStatus") String loanStatus);

    void insertLoanHist(LoanHistVO loanHistVO);
}
