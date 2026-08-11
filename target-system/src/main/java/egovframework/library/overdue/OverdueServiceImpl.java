package egovframework.library.overdue;

import java.util.Date;
import java.util.List;
import java.util.UUID;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import egovframework.library.cmmn.exception.BusinessException;
import egovframework.library.cmmn.exception.DataNotFoundException;
import egovframework.library.cmmn.util.DateUtil;
import egovframework.library.loan.LoanMapper;
import egovframework.library.loan.LoanStatus;
import egovframework.library.loan.LoanVO;
import egovframework.library.member.MemberMapper;
import egovframework.library.member.MemberStatus;

@Service("overdueService")
public class OverdueServiceImpl implements OverdueService {

    @Autowired
    private OverdueMapper overdueMapper;

    @Autowired
    private LoanMapper loanMapper;

    @Autowired
    private MemberMapper memberMapper;

    @Override
    public List<OverdueVO> selectOverdueList(OverdueSearchVO searchVO) {
        return overdueMapper.selectOverdueList(searchVO);
    }

    @Override
    public int selectOverdueListCount(OverdueSearchVO searchVO) {
        return overdueMapper.selectOverdueListCount(searchVO);
    }

    @Override
    public OverdueVO selectOverdue(String overdueId) {
        OverdueVO overdueVO = overdueMapper.selectOverdue(overdueId);
        if (overdueVO == null) {
            throw new DataNotFoundException("연체 정보를 찾을 수 없습니다. overdueId=" + overdueId);
        }
        return overdueVO;
    }

    @Override
    public List<OverdueVO> selectOverdueByMember(String memberId) {
        return overdueMapper.selectOverdueByMember(memberId);
    }

    @Override
    @Transactional
    public void updateRelease(String overdueId) {
        OverdueVO overdue = selectOverdue(overdueId);
        if (OverdueStatus.RELEASED.getCode().equals(overdue.getSanctionStatus())) {
            throw new BusinessException("ALREADY_RELEASED", "이미 해제 처리된 연체 건입니다.");
        }

        overdue.setReleaseDate(new Date());
        overdue.setSanctionStatus(OverdueStatus.RELEASED.getCode());
        overdueMapper.updateRelease(overdue);

        // 연체 해제 시 회원을 다시 정상 상태로 복원
        LoanVO loan = loanMapper.selectLoan(overdue.getLoanId());
        memberMapper.updateMemberStatus(loan.getMemberId(), MemberStatus.NORMAL.getCode());
    }

    @Override
    @Transactional
    public int refreshOverdueStatus() {
        int updatedCount = 0;

        // 반납예정일이 지났지만 아직 연체 등록되지 않은 대출 건 처리
        List<LoanVO> targetLoans = overdueMapper.selectOverdueTargetLoans();
        for (LoanVO loan : targetLoans) {
            int overdueDays = DateUtil.calcOverdueDays(loan.getDueDate(), new Date());

            OverdueVO overdueVO = new OverdueVO();
            overdueVO.setOverdueId("OD" + UUID.randomUUID().toString().substring(0, 8).toUpperCase());
            overdueVO.setLoanId(loan.getLoanId());
            overdueVO.setOverdueStartDate(DateUtil.addDays(loan.getDueDate(), 1));
            overdueVO.setOverdueDays(overdueDays);
            overdueVO.setSanctionStatus(OverdueStatus.SANCTIONED.getCode());
            overdueMapper.insertOverdue(overdueVO);

            loanMapper.updateLoanStatus(loan.getLoanId(), LoanStatus.OVERDUE.getCode());
            memberMapper.updateMemberStatus(loan.getMemberId(), MemberStatus.SUSPENDED.getCode());
            updatedCount++;
        }

        // 이미 연체 중(미해제)인 건들의 연체일수를 오늘 날짜 기준으로 재계산
        List<OverdueVO> activeList = overdueMapper.selectActiveOverdueList();
        for (OverdueVO overdue : activeList) {
            // OVERDUE_START_DATE = 반납예정일 + 1일이므로 +1을 보정해 연체일수를 구한다
            int overdueDays = DateUtil.calcOverdueDays(overdue.getOverdueStartDate(), new Date()) + 1;
            overdueMapper.updateOverdueDays(overdue.getOverdueId(), overdueDays);
            updatedCount++;
        }

        return updatedCount;
    }
}
