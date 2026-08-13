# [플랜 B] 장애 진단 — NPE (버그1)

화면이 안 뜰 때 이 페이지를 그대로 띄우거나 읽어주면 됩니다.
(2026-08-13 실측: 응답 27.5초, 10/10 시연 확정 — line 63 매번 정확히 특정)

---

**입력**: `target-system/demo/error_log_1.txt` (실제 재현한 진짜 스택트레이스)

---

## 1. 원인 분석
시스템에서 발생한 오류는 `NullPointerException`으로, `MemberVO` 객체의 `member` 변수가
`null` 상태에서 `member.getMemberStatus()` 메서드를 호출하려고 시도한 결과입니다. 이는
`LoanServiceImpl` 클래스의 `insertLoan` 메서드에서 회원 정보를 가져오는 과정에서 회원 정보가
제대로 로드되지 않았음을 의미합니다. 즉, `memberMapper.selectMember(loanVO.getMemberId())`
호출이 `null`을 반환했고, 이후 이 `null` 객체의 메서드를 호출하려고 했기 때문에 예외가
발생했습니다.

## 2. 문제 코드 위치
**파일명**: `src/main/java/egovframework/library/loan/LoanServiceImpl.java`
**라인번호**: 63

```java
MemberVO member = memberMapper.selectMember(loanVO.getMemberId());
if (!MemberStatus.NORMAL.getCode().equals(member.getMemberStatus())) {   // ← 63번 라인, NPE
    throw new LoanNotAllowedException("OVERDUE_MEMBER", "연체 중이거나 정상 상태가 아닌 회원은 대출할 수 없습니다.");
}
```
**문제점**: `memberMapper.selectMember()` 호출 결과가 `null`인데, 바로 `member.getMemberStatus()`를
호출해 `NullPointerException`이 발생합니다.

## 3. 수정 코드 제안
```java
MemberVO member = memberMapper.selectMember(loanVO.getMemberId());
if (member == null) {
    throw new LoanNotAllowedException("MEMBER_NOT_FOUND", "회원 정보를 찾을 수 없습니다.");
}
if (!MemberStatus.NORMAL.getCode().equals(member.getMemberStatus())) {
    throw new LoanNotAllowedException("OVERDUE_MEMBER", "연체 중이거나 정상 상태가 아닌 회원은 대출할 수 없습니다.");
}
```

---

### 호출 체인
`/loan/insertLoan.do` → `LoanController.insertLoan` → `LoanService.insertLoan` →
`LoanServiceImpl.insertLoan` → `BookMapper.selectBook` / `BookMapper.updateLoanYn` /
`LoanMapper.insertLoan` / `LoanMapper.insertLoanHist` / `LoanMapper.selectLoanCountByMember` /
`MemberMapper.selectMember`

### 발표용 한 줄 요약
"운영 중 발생한 실제 NPE 로그를 붙여넣으면, AI가 스택트레이스를 파싱해 정확한 파일·라인
(63번)까지 짚어내고, null 체크를 추가하는 수정 코드까지 즉시 제안합니다."
