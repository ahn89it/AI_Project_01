# [플랜 B 예비] Q&A — 회원은 몇 권까지 빌릴 수 있나요?

Q&A 응답이 60초를 넘거나 이상하면 이 질문으로 전환하세요.
(10/10, 평균 13.6초로 가장 빠르고 안정적)

---

**질문**: 회원은 몇 권까지 빌릴 수 있나요?

**답변**:
1) **처리 흐름 요약**: 사용자는 `/loan/checkLoanable.do`로 대출 가능 여부를 확인하거나
`/loan/insertLoan.do`로 대출을 신청합니다. 대출 처리 시, 회원의 대출 가능 권수는
`LibraryConstants`에서 정의된 `MAX_LOAN_COUNT` 상수에 따라 결정됩니다.

2) **상세 설명**: 회원이 빌릴 수 있는 최대 도서 권수는 `LibraryConstants` 클래스에서 정의된
`MAX_LOAN_COUNT` 상수에 의해 결정됩니다. 코드에서 `MAX_LOAN_COUNT`는 `5`로 설정되어
있습니다. 즉, **회원은 최대 5권까지 도서를 빌릴 수 있습니다**. 대출 처리 로직에서는
`loanMapper.selectLoanCountByMember(memberId, loanStatus)`를 통해 해당 회원의 현재 대출
권수를 확인하고, 이 값이 `MAX_LOAN_COUNT`보다 작은지 검사합니다.

3) **결론**: 회원은 **최대 5권**까지 도서를 빌릴 수 있습니다.

**근거**: `LibraryConstants.java:6-19` (`MAX_LOAN_COUNT = 5`),
`LoanServiceImpl.insertLoan`, `LoanServiceImpl.checkLoanable`
