package egovframework.library.loan;

import java.util.Date;
import java.util.List;
import java.util.UUID;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import egovframework.library.book.BookMapper;
import egovframework.library.book.BookVO;
import egovframework.library.cmmn.exception.DataNotFoundException;
import egovframework.library.cmmn.util.DateUtil;
import egovframework.library.cmmn.util.LibraryConstants;
import egovframework.library.member.MemberMapper;
import egovframework.library.member.MemberStatus;
import egovframework.library.member.MemberVO;
import egovframework.library.overdue.OverdueMapper;
import egovframework.library.overdue.OverdueVO;

@Service("loanService")
public class LoanServiceImpl implements LoanService {

    @Autowired
    private LoanMapper loanMapper;

    // 회원/도서 매퍼를 서비스 계층을 거치지 않고 직접 참조한다.
    // (member/book 도메인과 강하게 얽혀 있는 대출 처리 특성상 흔히 이렇게 구성됨)
    @Autowired
    private MemberMapper memberMapper;

    @Autowired
    private BookMapper bookMapper;

    @Autowired
    private OverdueMapper overdueMapper;

    @Override
    public List<LoanVO> selectLoanList(LoanSearchVO searchVO) {
        return loanMapper.selectLoanList(searchVO);
    }

    @Override
    public int selectLoanListCount(LoanSearchVO searchVO) {
        return loanMapper.selectLoanListCount(searchVO);
    }

    @Override
    public LoanVO selectLoan(String loanId) {
        LoanVO loanVO = loanMapper.selectLoan(loanId);
        if (loanVO == null) {
            throw new DataNotFoundException("대출 정보를 찾을 수 없습니다. loanId=" + loanId);
        }
        return loanVO;
    }

    @Override
    @Transactional
    public LoanResultVO insertLoan(LoanVO loanVO) {
        // 회원 상태 확인 - 연체 중인 회원은 대출 불가 처리
        MemberVO member = memberMapper.selectMember(loanVO.getMemberId());
        if (!MemberStatus.NORMAL.getCode().equals(member.getMemberStatus())) {
            throw new LoanNotAllowedException("OVERDUE_MEMBER", "연체 중이거나 정상 상태가 아닌 회원은 대출할 수 없습니다.");
        }

        // 대출 중인 도서 권수 확인 - 1인 최대 5권
        int loanCount = loanMapper.selectLoanCountByMember(loanVO.getMemberId(), LoanStatus.LOANED.getCode());
        if (loanCount >= LibraryConstants.MAX_LOAN_COUNT) {
            throw new LoanNotAllowedException("LOAN_LIMIT_EXCEEDED",
                    "1인당 최대 " + LibraryConstants.MAX_LOAN_COUNT + "권까지만 대출 가능합니다.");
        }

        // 대출 대상 도서 조회
        BookVO book = bookMapper.selectBook(loanVO.getBookId());

        // 대출 등록
        loanVO.setLoanId("LN" + UUID.randomUUID().toString().substring(0, 8).toUpperCase());
        loanVO.setLoanDate(new Date());
        loanVO.setDueDate(DateUtil.calcDueDate(loanVO.getLoanDate()));
        loanVO.setLoanStatus(LoanStatus.LOANED.getCode());
        loanVO.setExtendCnt(0);
        loanMapper.insertLoan(loanVO);

        // 도서 상태를 대출중으로 변경
        bookMapper.updateLoanYn(book.getBookId(), "N");

        // 대출 이력 기록
        LoanHistVO hist = new LoanHistVO();
        hist.setHistId("LH" + UUID.randomUUID().toString().substring(0, 8).toUpperCase());
        hist.setLoanId(loanVO.getLoanId());
        hist.setProcessType(LoanHistVO.TYPE_LOAN);
        hist.setProcessor("SYSTEM");
        loanMapper.insertLoanHist(hist);

        return new LoanResultVO(true, "대출이 완료되었습니다.", null);
    }

    @Override
    @Transactional
    public void updateReturn(String loanId) {
        LoanVO loan = selectLoan(loanId);

        Date returnDate = new Date();
        loan.setReturnDate(returnDate);
        loan.setLoanStatus(LoanStatus.RETURNED.getCode());
        loanMapper.updateReturn(loan);

        // 도서를 다시 대출가능 상태로 복원
        bookMapper.updateLoanYn(loan.getBookId(), "Y");

        // 반납예정일을 초과했다면 연체 등록 + 회원 대출정지 처리
        if (returnDate.after(loan.getDueDate())) {
            int overdueDays = DateUtil.calcOverdueDays(loan.getDueDate(), returnDate);

            OverdueVO overdueVO = new OverdueVO();
            overdueVO.setOverdueId("OD" + UUID.randomUUID().toString().substring(0, 8).toUpperCase());
            overdueVO.setLoanId(loan.getLoanId());
            overdueVO.setOverdueStartDate(DateUtil.addDays(loan.getDueDate(), 1));
            overdueVO.setOverdueDays(overdueDays);
            overdueVO.setSanctionStatus("1");
            overdueMapper.insertOverdue(overdueVO);

            // 연체 중인 회원은 대출 불가 처리를 위해 대출정지 상태로 변경
            memberMapper.updateMemberStatus(loan.getMemberId(), MemberStatus.SUSPENDED.getCode());
        }

        // 반납 이력 기록
        LoanHistVO hist = new LoanHistVO();
        hist.setHistId("LH" + UUID.randomUUID().toString().substring(0, 8).toUpperCase());
        hist.setLoanId(loan.getLoanId());
        hist.setProcessType(LoanHistVO.TYPE_RETURN);
        hist.setProcessor("SYSTEM");
        loanMapper.insertLoanHist(hist);
    }

    @Override
    @Transactional
    public void updateExtend(String loanId) {
        LoanVO loan = selectLoan(loanId);
        if (!LoanStatus.LOANED.getCode().equals(loan.getLoanStatus())) {
            throw new LoanNotAllowedException("EXTEND_NOT_ALLOWED", "대출중 상태가 아닌 건은 연장할 수 없습니다.");
        }

        loan.setDueDate(DateUtil.extendDueDate(loan.getDueDate()));
        loan.setExtendCnt(loan.getExtendCnt() + 1);
        loanMapper.updateExtend(loan);

        LoanHistVO hist = new LoanHistVO();
        hist.setHistId("LH" + UUID.randomUUID().toString().substring(0, 8).toUpperCase());
        hist.setLoanId(loan.getLoanId());
        hist.setProcessType(LoanHistVO.TYPE_EXTEND);
        hist.setProcessor("SYSTEM");
        loanMapper.insertLoanHist(hist);
    }

    @Override
    public LoanResultVO checkLoanable(String memberId) {
        MemberVO member = memberMapper.selectMember(memberId);
        if (member == null) {
            return new LoanResultVO(false, "존재하지 않는 회원입니다.", "MEMBER_NOT_FOUND");
        }
        if (!MemberStatus.NORMAL.getCode().equals(member.getMemberStatus())) {
            return new LoanResultVO(false, "연체 중이거나 정상 상태가 아닌 회원입니다.", "OVERDUE_MEMBER");
        }
        int loanCount = loanMapper.selectLoanCountByMember(memberId, LoanStatus.LOANED.getCode());
        if (loanCount >= LibraryConstants.MAX_LOAN_COUNT) {
            return new LoanResultVO(false, "최대 대출 권수를 초과했습니다.", "LOAN_LIMIT_EXCEEDED");
        }
        return new LoanResultVO(true, "대출 가능합니다.", null);
    }
}
