package egovframework.library.overdue;

import java.util.List;

public interface OverdueService {

    List<OverdueVO> selectOverdueList(OverdueSearchVO searchVO);

    int selectOverdueListCount(OverdueSearchVO searchVO);

    OverdueVO selectOverdue(String overdueId);

    List<OverdueVO> selectOverdueByMember(String memberId);

    /**
     * 연체 해제 처리. 제재상태를 해제로 변경하고 회원상태를 정상으로 복원한다.
     */
    void updateRelease(String overdueId);

    /**
     * 연체 상태 일괄 갱신 배치. 새로 연체가 발생한 대출 건을 TB_OVERDUE에 등록하고,
     * 이미 연체 중인 건들의 연체일수를 오늘 날짜 기준으로 재계산한다.
     *
     * @return 갱신된 건수
     */
    int refreshOverdueStatus();
}
