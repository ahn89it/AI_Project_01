# 장애 진단 데모 결과 — 버그 1 (NPE)

D8 완료 기준 테스트 1 실행 결과 전문. 발표 자료 "장애 진단" 페이지, D13 리허설 대본 재료용.
스크린샷 대신 텍스트로 기록 (2026-08-11, `POST /api/diagnose`에 `demo/error_log_1.txt` 투입,
응답 39.2초).

## 입력
`demo/error_log_1.txt` 전문 (D3에서 실제 NPE를 재현해 얻은 진짜 스택트레이스 기반 로그)

## 출력 — error_location (BUGS.md 버그 1 위치와 정확히 일치)
```json
{
  "file": "src/main/java/egovframework/library/loan/LoanServiceImpl.java",
  "line": 63,
  "class_method": "LoanServiceImpl.insertLoan"
}
```

## 출력 — call_chain
```
/loan/insertLoan.do → LoanController.insertLoan → LoanService.insertLoan
→ LoanServiceImpl.insertLoan → (BookMapper.selectBook, BookMapper.updateLoanYn,
   LoanMapper.insertLoan, LoanMapper.insertLoanHist, LoanMapper.selectLoanCountByMember,
   MemberMapper.selectMember)
```

## 출력 — diagnosis (EXAONE 3.5 7.8B, temperature 0.2)

### 1. 원인 분석
예외 메시지 `java.lang.NullPointerException: Cannot invoke "egovframework.library.member.MemberVO.getMemberStatus()" because "member" is null`은 `LoanServiceImpl` 클래스의 `insertLoan` 메서드에서 `member` 객체가 `null` 상태로 처리되고 있다는 것을 나타냅니다. 이 메서드 내에서 `memberMapper.selectMember(loanVO.getMemberId())` 호출 결과가 `null`로 반환되었고, 그 결과 `member.getMemberStatus()`를 호출하려고 시도하면서 `NullPointerException`이 발생했습니다.

### 2. 문제 코드 위치
**`src/main/java/egovframework/library/loan/LoanServiceImpl.java:63`**
```java
MemberVO member = memberMapper.selectMember(loanVO.getMemberId());
>>> if (!MemberStatus.NORMAL.getCode().equals(member.getMemberStatus())) {
    throw new LoanNotAllowedException("OVERDUE_MEMBER", "연체 중이거나 정상 상태가 아닌 회원은 대출할 수 없습니다.");
}
```
**문제점:** `memberMapper.selectMember` 호출 결과가 `null`일 수 있는데 이를 확인하지 않고 바로 `getMemberStatus()`를 호출해 예외가 발생합니다.

### 3. 수정 코드 제안
```java
MemberVO member = memberMapper.selectMember(loanVO.getMemberId());
if (member == null) {
    throw new RuntimeException("회원 정보를 가져올 수 없습니다: " + loanVO.getMemberId());
}
if (!MemberStatus.NORMAL.getCode().equals(member.getMemberStatus())) {
    throw new LoanNotAllowedException("OVERDUE_MEMBER", "연체 중이거나 정상 상태가 아닌 회원은 대출할 수 없습니다.");
}
```

### 4. 재발 방지 (원문 헤더는 "추가 고려사항"으로 출력됨 — 아래 참고)
- 로깅: 예외 발생 시 로깅을 통해 문제 발생 시점과 원인을 추적할 수 있도록 한다
- 유효성 검사: `memberMapper.selectMember` 호출 전후로 결과 null 여부를 검사하는 관례를 표준화한다

## 완료 기준 대조
| 항목 | 판정 |
|---|---|
| (a) error_location이 BUGS.md 버그1 위치와 일치 | ✅ 정확히 일치 (LoanServiceImpl.java:63) |
| (b) 원인 분석에 "NULL 체크 누락" 취지 포함 | ✅ "null인지 확인하지 않고 바로 호출" 명시 |
| (c) 수정 코드가 null 체크 추가 방향 | ✅ `if (member == null) { throw ... }` 제시 |
| (d) call_chain에 URL부터 흐름 표시 | ✅ `/loan/insertLoan.do`부터 전부 포함 |

**참고**: 4단 구조의 4번째 제목을 스펙대로 "재발 방지"가 아니라 "추가 고려사항"으로 출력함
(내용 자체는 재발 방지 지침과 동일). 기능적으로는 문제 없어 추가 튜닝하지 않음 — 시연 때
헤더 문구 차이는 발표자가 자연스럽게 넘어가면 됨.

## 참고: 테스트 2(중복 대출 버그, 보너스)는 시연 미채택
"같은 책이 두 번 대출되는 문제..." 질문을 `/api/rag/ask`에 투입한 결과, EXAONE이 실제 원인
(도서 `LOAN_YN` 검증 누락)을 짚지 못하고 트랜잭션/동시성 등 무관한 가설로 빠졌으며 존재하지
않는 `EntityManager` 기반 코드까지 지어냄. tip 지침대로 더 튜닝하지 않고 시연에서 제외,
테스트 1(NPE) 중심으로 진행하기로 함.
