# 의도적 버그 목록 (시연용)

이 파일은 장애 진단 기능 시연을 위해 의도적으로 삽입한 버그의 위치와 재현 방법을 기록합니다.
**analyzer 인덱싱 대상에서 제외**합니다 (정답지를 AI가 미리 학습하지 않도록).

---

## 버그 1: NPE — 회원 NULL 체크 누락

- **위치**: [`src/main/java/egovframework/library/loan/LoanServiceImpl.java`](src/main/java/egovframework/library/loan/LoanServiceImpl.java) `insertLoan()` 메서드, **63번 라인**
- **원인 코드**:
  ```java
  MemberVO member = memberMapper.selectMember(loanVO.getMemberId());   // 62번 라인
  if (!MemberStatus.NORMAL.getCode().equals(member.getMemberStatus())) {  // 63번 라인 <- 여기서 NPE
  ```
  `memberMapper.selectMember()`는 대상이 없으면 MyBatis 규약상 `null`을 반환하는데,
  이 결과에 대한 null 체크 없이 바로 `member.getMemberStatus()`를 호출한다.
- **재현 방법**: `/loan/insertLoan.do`에 존재하지 않는 `memberId`(예: `MB99999`)로 POST 요청
- **기대 동작(수정 후)**: 존재하지 않는 회원이면 `DataNotFoundException` 등을 던져 "회원을 찾을 수
  없습니다" 형태의 업무 예외로 처리되어야 함 (같은 클래스의 `checkLoanable()` 메서드는 이미
  올바르게 null 체크를 하고 있어 참고 가능)
- **실제 발생 시 로그**: [`demo/error_log_1.txt`](demo/error_log_1.txt) 참고. 리플렉션으로
  `LoanServiceImpl`을 직접 호출해 실제로 재현시킨 뒤 얻은 진짜 스택트레이스이며,
  `LoanServiceImpl.java:63`, `LoanController.java:54` 라인은 실제 소스와 정확히 일치한다.

## 버그 2: 데이터 정합성 — 중복 대출 체크 누락

- **위치**: [`src/main/java/egovframework/library/loan/LoanServiceImpl.java`](src/main/java/egovframework/library/loan/LoanServiceImpl.java) `insertLoan()` 메서드, **74~86번 라인**
- **원인 코드**:
  ```java
  // 대출 대상 도서 조회
  BookVO book = bookMapper.selectBook(loanVO.getBookId());   // 75번 라인: 조회만 하고

  // 대출 등록
  ...
  loanMapper.insertLoan(loanVO);                              // 83번 라인: 검증 없이 바로 등록

  // 도서 상태를 대출중으로 변경
  bookMapper.updateLoanYn(book.getBookId(), "N");             // 86번 라인: 이미 N이어도 그대로 진행
  ```
  `book.getLoanYn()` 값(대출가능여부)을 확인하는 조건문이 없다. 이미 대출 중(`LOAN_YN='N'`)인
  도서에 대해서도 대출 등록이 그대로 진행되어, 동일 도서에 대해 `LOAN_STATUS='1'`(대출중)인
  `TB_LOAN` 레코드가 2건 이상 존재할 수 있다.
- **재현 방법**: 이미 대출 중인 `bookId`(예: seed 데이터 중 `LOAN_YN='N'`인 도서)로
  `/loan/insertLoan.do`를 두 번 연속 POST. 예외 없이 두 건 모두 성공 처리됨
- **특징**: 예외가 발생하지 않고 "잘못된 데이터가 조용히 쌓이는" 유형이라 에러 로그로는
  발견되지 않는다. `SELECT BOOK_ID, COUNT(*) FROM TB_LOAN WHERE LOAN_STATUS='1' GROUP BY BOOK_ID
  HAVING COUNT(*) > 1` 같은 조회 또는 코드 리뷰(정적 분석)로만 발견 가능 — 코드 분석 기반
  장애 진단 기능의 시연 포인트
- **기대 동작(수정 후)**: `book.getLoanYn()`이 `'Y'`가 아니면 `LoanNotAllowedException` 등을
  던져 등록을 차단해야 함
