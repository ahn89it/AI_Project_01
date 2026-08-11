package egovframework.library.overdue;

import java.util.List;

import org.apache.ibatis.annotations.Param;

import egovframework.library.loan.LoanVO;

/**
 * 연체(TB_OVERDUE) MyBatis 매퍼 인터페이스.
 * 실제 SQL은 resources/mappers/Overdue_SQL.xml 참조.
 */
public interface OverdueMapper {

    List<OverdueVO> selectOverdueList(OverdueSearchVO searchVO);

    int selectOverdueListCount(OverdueSearchVO searchVO);

    OverdueVO selectOverdue(@Param("overdueId") String overdueId);

    List<OverdueVO> selectOverdueByMember(@Param("memberId") String memberId);

    void insertOverdue(OverdueVO overdueVO);

    void updateRelease(OverdueVO overdueVO);

    void updateOverdueDays(@Param("overdueId") String overdueId, @Param("overdueDays") int overdueDays);

    /**
     * 반납예정일이 지났지만 아직 TB_OVERDUE에 등록되지 않은 대출 건 조회 (연체 상태 일괄 갱신 배치용).
     */
    List<LoanVO> selectOverdueTargetLoans();

    /**
     * 아직 해제되지 않은(제재중) 연체 건 목록 조회 (연체일수 재계산 배치용).
     */
    List<OverdueVO> selectActiveOverdueList();
}
