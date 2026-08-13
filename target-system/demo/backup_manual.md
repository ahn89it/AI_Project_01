# 도서관 관리 시스템 업무 매뉴얼

- 생성일시: 2026-08-13T22:06:40.034848
- 분석 대상: target-system/ (AI가 소스코드를 자동 분석해 작성한 문서입니다)
- 대상 URL 수: 22개

## 1. 시스템 개요

자동 분석된 업무 도메인 (URL 22개, 테이블 6개):

- **도서 관리**: 기능 6개
- **회원 관리**: 기능 5개
- **대출·반납**: 기능 6개
- **연체 관리**: 기능 5개

## 2. 도서 관리

### 도서 삭제
- 화면 경로: `/book/deleteBook.do`
- 처리 절차:
1. **도서 삭제 요청**: 사용자가 `/book/deleteBook.do` 화면을 통해 특정 도서의 삭제를 요청합니다.
2. **도서 정보 확인**: 시스템은 요청된 도서 ID를 기반으로 `selectBook` 메서드를 호출하여 해당 도서의 정보를 확인합니다.
3. **도서 존재 검증**: `selectBook` 메서드에서 도서 정보가 존재하지 않으면 (`bookVO == null`), `BookNotFoundException`이 발생하여 삭제 요청이 중단됩니다.
4. **도서 삭제 실행**: 도서 정보가 확인되면, `deleteBook` 메서드가 호출되어 `bookMapper.deleteBook(bookId)`를 통해 실제 데이터베이스에서 해당 도서의 정보가 삭제됩니다.
5. **삭제 완료 확인**: 삭제 작업이 성공적으로 완료되면, 시스템은 해당 요청을 종료하고 사용자에게 삭제 완료 메시지를 제공합니다 (코드 내에서는 명시되지 않았으나 일반적인 처리 흐름).
- 관련 테이블: TB_BOOK, TB_CATEGORY
- 참고: 처리 흐름 — BookController.deleteBook → BookServiceImpl.deleteBook → BookServiceImpl.selectBook → SQL 2건

### 도서 등록
- 화면 경로: `/book/insertBook.do`
- 처리 절차:
1. **도서 등록 시작**: 도서 등록 화면(/book/insertBook.do)에서 새로운 도서 정보를 입력합니다.
2. **도서 ID 자동 생성**: 
   - 만약 입력된 도서 ID가 비어 있거나 없으면 (`bookVO.getBookId() == null || bookVO.getBookId().isEmpty()`), 시스템은 자동으로 새로운 고유 ID를 생성합니다 (예: "BK"로 시작하는 8자리 대문자 코드).
3. **대출 여부 설정**:
   - 만약 대출 여부 항목(`bookVO.getLoanYn()`)이 비어 있거나 설정되지 않았다면, 기본값으로 "대출 가능" (`"Y"`)으로 설정합니다.
4. **도서 정보 저장**: 처리된 도서 정보(`bookVO`)를 `bookMapper.insertBook` 메서드를 통해 데이터베이스에 저장합니다.
5. **처리 완료 확인**: 도서 정보 저장이 성공적으로 완료되면 등록 절차가 종료됩니다. 만약 저장 과정에서 오류가 발생하면 해당 오류 메시지를 확인하고 필요한 조치를 취해야 합니다.
- 관련 테이블: TB_BOOK
- 참고: 처리 흐름 — BookController.insertBook → BookServiceImpl.insertBook → SQL 1건

### 도서 상세 조회
- 화면 경로: `/book/selectBookDetail.do`
- 처리 절차:
1. **도서 검색 요청**: 사용자가 도서 상세 정보 페이지 (URL: /book/selectBookDetail.do)에서 특정 도서 ID를 입력하거나 선택합니다.

2. **도서 정보 요청 전송**: 시스템은 입력된 도서 ID를 기반으로 도서 정보 요청을 처리 모듈 (BookServiceImpl)에 전달합니다.

3. **도서 정보 조회**: 처리 모듈 내에서 `BookMapper`를 통해 데이터베이스에서 해당 도서 ID의 정보를 조회합니다.

4. **결과 검증**: 조회된 도서 정보 (`BookVO` 객체)가 존재하지 않는 경우 (`bookVO == null`):
   - **예외 발생**: `BookNotFoundException`이 발생하여 시스템은 오류 메시지를 생성하고 처리를 중단합니다.

5. **정보 반환**: 도서 정보가 성공적으로 조회되면, 해당 `BookVO` 객체를 사용자 인터페이스로 반환하여 도서 상세 정보를 표시합니다.
- 관련 테이블: TB_BOOK, TB_CATEGORY
- 참고: 처리 흐름 — BookController.selectBookDetail → BookServiceImpl.selectBook → SQL 1건

### 도서 목록 조회
- 화면 경로: `/book/selectBookList.do`
- 처리 절차:
1. 입력된 검색 조건에 맞는 데이터를 조회합니다.
2. 조회된 결과를 반환합니다.
- 관련 테이블: TB_BOOK, TB_CATEGORY
- 참고: 처리 흐름 — BookController.selectBookList → BookServiceImpl.selectBookList → BookServiceImpl.selectBookListCount → SQL 2건

### 도서 분류 목록 조회
- 화면 경로: `/book/selectCategoryList.do`
- 처리 절차:
1. 입력된 검색 조건에 맞는 데이터를 조회합니다.
2. 조회된 결과를 반환합니다.
- 관련 테이블: TB_CATEGORY
- 참고: 처리 흐름 — BookController.selectCategoryList → BookServiceImpl.selectCategoryList → SQL 1건

### 도서 정보 수정
- 화면 경로: `/book/updateBook.do`
- 처리 절차:
1. **도서 정보 수정 요청**: 수정하고자 하는 도서의 고유 식별자(ID)를 포함한 도서 정보(BookVO)를 준비합니다.

2. **도서 존재 확인**: 준비된 도서 ID를 기반으로 시스템 내에서 해당 도서의 존재 여부를 확인합니다.
   - 만약 해당 도서 ID로 검색된 도서 정보가 없다면, "도서 미발견 오류"가 발생하고 처리가 중단됩니다.

3. **도서 정보 업데이트**: 도서가 존재하는 경우, 준비된 도서 정보를 바탕으로 시스템 내에서 해당 도서의 정보를 업데이트합니다.
   - 업데이트 작업은 트랜잭션 처리 하에 이루어집니다.

4. **업데이트 완료 확인**: 업데이트 과정이 성공적으로 완료되면 시스템은 변경 사항을 반영한 최신 도서 정보를 저장합니다.
   - 만약 업데이트 과정에서 오류가 발생하면 해당 오류에 따라 적절한 조치를 취해야 합니다. (코드에서는 구체적인 오류 처리 로직이 명시되어 있지 않음)
- 관련 테이블: TB_BOOK, TB_CATEGORY
- 참고: 처리 흐름 — BookController.updateBook → BookServiceImpl.selectBook → BookServiceImpl.updateBook → SQL 2건

## 3. 회원 관리

### 회원 삭제
- 화면 경로: `/member/deleteMember.do`
- 처리 절차:
1. **회원 정보 확인**: 회원 삭제를 요청한 경우, 해당 회원의 ID(memberId)를 기반으로 시스템 내 회원 정보를 확인합니다.
2. **회원 존재 검증**: 확인된 회원 정보가 존재하지 않는 경우 (즉, memberId에 해당하는 회원이 없는 경우), "회원을 찾을 수 없습니다."라는 메시지와 함께 해당 회원 ID를 표시하여 오류를 발생시킵니다.
3. **회원 정보 삭제 요청**: 회원 정보가 존재하는 경우, 시스템은 해당 회원 정보의 삭제를 요청합니다. 이 요청은 `memberMapper.deleteMember(memberId)`를 통해 처리됩니다.
4. **삭제 처리 완료**: 삭제 요청이 성공적으로 처리되면, 시스템은 해당 회원 정보의 데이터베이스에서 영구적으로 제거됩니다.
5. **처리 완료 확인**: 삭제 작업이 완료되면, 시스템은 해당 회원 ID에 대한 접근이 더 이상 불가능하도록 설정되어 업무 처리가 완료됩니다.
- 관련 테이블: TB_MEMBER
- 참고: 처리 흐름 — MemberController.deleteMember → MemberServiceImpl.deleteMember → MemberServiceImpl.selectMember → SQL 2건

### 회원 등록
- 화면 경로: `/member/insertMember.do`
- 처리 절차:
1. **회원 정보 입력 화면 접근**  
   회원 정보 입력을 위한 `/member/insertMember.do` 화면으로 이동합니다.

2. **필수 회원 정보 입력**  
   회원 ID와 회원 상태를 포함한 필수 정보를 입력합니다.

3. **회원 ID 자동 생성**  
   - 만약 회원 ID가 입력되지 않았거나 비어 있다면, 시스템은 자동으로 "MB"로 시작하는 고유한 8자리 대문자 코드를 생성하여 회원 ID로 설정합니다.

4. **회원 상태 설정**  
   - 회원 상태가 입력되지 않았거나 비어 있다면, 시스템은 기본 상태인 "정상" (NORMAL)으로 자동 설정합니다.

5. **회원 정보 저장 요청**  
   입력된 회원 정보를 `MemberServiceImpl.insertMember` 메서드를 통해 데이터베이스에 저장 요청합니다. 이 과정은 트랜잭션으로 관리되어 안정적으로 처리됩니다.

6. **처리 완료 확인**  
   회원 정보 저장이 성공적으로 완료되면, 시스템은 저장 완료 메시지를 표시합니다. 만약 입력 오류가 있으면 해당 오류 메시지를 통해 수정을 요청합니다.
- 관련 테이블: TB_MEMBER
- 참고: 처리 흐름 — MemberController.insertMember → MemberServiceImpl.insertMember → SQL 1건

### 회원 상세 조회
- 화면 경로: `/member/selectMemberDetail.do`
- 처리 절차:
1. **회원 정보 요청**: 회원 ID를 입력합니다.
2. **회원 정보 검색**: 시스템은 입력된 회원 ID를 기반으로 데이터베이스에서 해당 회원 정보를 검색합니다.
3. **정보 존재 확인**: 검색 결과, 회원 정보가 존재하지 않는 경우 (즉, 입력된 회원 ID에 해당하는 회원이 없는 경우) 데이터 미발견 예외가 발생합니다.
4. **정보 반환**: 회원 정보가 발견되면 해당 정보를 포함한 `MemberVO` 객체를 생성하여 반환합니다.
- 관련 테이블: TB_MEMBER
- 참고: 처리 흐름 — MemberController.selectMemberDetail → MemberServiceImpl.selectMember → SQL 1건

### 회원 목록 조회
- 화면 경로: `/member/selectMemberList.do`
- 처리 절차:
1. 입력된 검색 조건에 맞는 데이터를 조회합니다.
2. 조회된 결과를 반환합니다.
- 관련 테이블: TB_MEMBER
- 참고: 처리 흐름 — MemberController.selectMemberList → MemberServiceImpl.selectMemberList → MemberServiceImpl.selectMemberListCount → SQL 2건

### 회원 정보 수정
- 화면 경로: `/member/updateMember.do`
- 처리 절차:
1. **회원 정보 수정 요청**: 회원 정보 수정을 위한 요청이 발생합니다.
2. **회원 정보 확인**: 시스템은 요청된 회원 ID를 기반으로 `MemberServiceImpl.selectMember` 메서드를 호출하여 해당 회원 정보를 확인합니다.
3. **회원 존재 검증**: 
   - 만약 회원 정보가 존재하지 않으면 (`memberVO == null`), 시스템은 `DataNotFoundException`을 발생시켜 처리를 중단하고 오류 메시지를 표시합니다: "회원을 찾을 수 없습니다. memberId=[입력된 회원 ID]".
4. **회원 정보 업데이트**: 회원 정보가 존재하는 경우, `MemberServiceImpl.updateMember` 메서드를 통해 회원 정보를 수정합니다. 이 과정은 트랜잭션 처리 하에 이루어집니다.
5. **수정 완료 확인**: 업데이트가 성공적으로 완료되면 시스템은 변경 사항을 저장하고 사용자에게 수정 완료 메시지를 제공합니다. (코드 내에서는 명시적으로 확인 메시지 제공은 언급되지 않았으나, 일반적인 시스템 동작에 따라 이 단계가 포함될 수 있습니다.)
- 관련 테이블: TB_MEMBER
- 참고: 처리 흐름 — MemberController.updateMember → MemberServiceImpl.selectMember → MemberServiceImpl.updateMember → SQL 2건

## 4. 대출·반납

### 대출 가능 여부 확인
- 화면 경로: `/loan/checkLoanable.do`
- 처리 절차:
1. **회원 정보 확인**: 회원 ID를 입력받아 시스템 내 회원 데이터베이스에서 해당 회원의 정보를 조회합니다.
2. **회원 존재 여부 검증**: 조회된 회원 정보가 없는 경우 (회원이 존재하지 않음), 대출 가능 여부를 **거짓**으로 판단하고 오류 메시지 "존재하지 않는 회원입니다."와 코드 "MEMBER_NOT_FOUND"를 반환합니다.
3. **회원 상태 검증**: 회원이 정상 상태가 아닌 경우 (예: 연체 상태 등), 대출 가능 여부를 **거짓**으로 판단하고 오류 메시지 "연체 중이거나 정상 상태가 아닌 회원입니다."와 코드 "OVERDUE_MEMBER"를 반환합니다.
4. **대출 권수 확인**: 해당 회원의 현재 대출 권수를 확인합니다. 만약 현재 대출 권수가 시스템 설정된 최대 대출 권수 (`LibraryConstants.MAX_LOAN_COUNT`)를 초과한 경우, 대출 가능 여부를 **거짓**으로 판단하고 오류 메시지 "최대 대출 권수를 초과했습니다."와 코드 "LOAN_LIMIT_EXCEEDED"를 반환합니다.
5. **대출 가능 확인 및 결과 반환**: 위의 모든 검증을 통과한 경우, 해당 회원에 대해 대출이 가능하다는 결과를 **참**으로 반환하고 메시지 "대출 가능합니다."를 함께 제공합니다.
- 관련 테이블: TB_LOAN, TB_MEMBER
- 참고: 처리 흐름 — LoanController.checkLoanable → LoanServiceImpl.checkLoanable → SQL 2건

### 도서 대출 등록
- 화면 경로: `/loan/insertLoan.do`
- 처리 절차:
1. **회원 정보 확인**  
   회원 ID를 기반으로 회원 상태를 확인합니다. 연체 중인 회원은 대출이 거부됩니다.

2. **대출 한도 확인**  
   현재 대출 중인 도서 권수를 확인합니다. 회원이 최대 대출 가능 권수 (5권)를 초과하면 대출이 거부됩니다.

3. **도서 정보 조회**  
   대출 신청한 도서의 정보를 조회합니다.

4. **대출 정보 생성 및 등록**  
   - 대출 고유 ID 생성 (예: "LNXXXXXXXX")
   - 대출 날짜 설정 (현재 날짜)
   - 반납 예정일 계산 (대출 날짜 기준)
   - 대출 상태를 '대출 완료'로 설정
   - 대출 정보를 데이터베이스에 등록합니다.

5. **도서 상태 업데이트**  
   대출된 도서의 상태를 '대출 중'으로 변경합니다.

6. **대출 이력 기록**  
   대출 이력을 기록합니다. 기록 내용은 다음과 같습니다:
   - 고유 이력 ID 생성 (예: "LHXXXXXXXX")
   - 대출 ID 할당
   - 프로세스 유형을 '대출'로 설정
   - 처리자를 '시스템'으로 기록
   - 대출 이력을 데이터베이스에 등록합니다.

7. **대출 완료 응답**  
   대출 처리가 성공적으로 완료되었음을 나타내는 결과 메시지를 반환합니다.
- 관련 테이블: TB_BOOK, TB_CATEGORY, TB_LOAN, TB_LOAN_HIST, TB_MEMBER
- 참고: 처리 흐름 — LoanController.insertLoan → LoanServiceImpl.insertLoan → SQL 6건

### 대출 상세 조회
- 화면 경로: `/loan/selectLoanDetail.do`
- 처리 절차:
1. **대출 정보 요청**: 대출 ID를 입력합니다.
2. **대출 정보 검색**: 시스템은 입력된 대출 ID를 기반으로 대출 정보를 검색합니다.
3. **정보 확인**: 검색된 대출 정보가 존재하는지 확인합니다.
   - **예외 처리**: 대출 ID에 해당하는 정보가 없을 경우, "대출 정보를 찾을 수 없습니다."라는 메시지와 함께 오류가 발생합니다.
4. **정보 반환**: 대출 정보가 존재하면 해당 정보를 LoanVO 객체로 포장하여 반환합니다.
- 관련 테이블: TB_BOOK, TB_LOAN, TB_MEMBER
- 참고: 처리 흐름 — LoanController.selectLoanDetail → LoanServiceImpl.selectLoan → SQL 1건

### 대출 목록 조회
- 화면 경로: `/loan/selectLoanList.do`
- 처리 절차:
1. 입력된 검색 조건에 맞는 데이터를 조회합니다.
2. 조회된 결과를 반환합니다.
- 관련 테이블: TB_BOOK, TB_LOAN, TB_MEMBER
- 참고: 처리 흐름 — LoanController.selectLoanList → LoanServiceImpl.selectLoanList → LoanServiceImpl.selectLoanListCount → SQL 2건

### 대출 연장 처리
- 화면 경로: `/loan/updateExtend.do`
- 처리 절차:
1. **대출 연장 요청 시작**  
   대출 연장을 위해 `/loan/updateExtend.do` 화면에서 대출 ID를 입력합니다.

2. **대출 정보 확인**  
   시스템은 입력된 대출 ID를 기반으로 `selectLoan` 메서드를 호출하여 해당 대출 정보를 조회합니다.

3. **대출 상태 검증**  
   조회된 대출 정보의 상태가 `대출중` 상태(`LoanStatus.LOANED`)가 아닌 경우, 대출 연장이 불가능하다는 메시지와 함께 `LoanNotAllowedException`이 발생합니다.

4. **연장 기간 설정**  
   대출 상태가 유효한 경우, 시스템은 현재 만기일(`DueDate`)을 연장하고 연장 횟수(`ExtendCnt`)를 1 증가시킵니다.

5. **데이터 업데이트**  
   연장된 대출 정보를 데이터베이스에 업데이트합니다 (`loanMapper.updateExtend` 호출).

6. **연장 이력 기록**  
   연장 처리를 기록하기 위해 새로운 연장 이력 정보(`LoanHistVO`)를 생성합니다. 이 정보에는 연장 고유 ID, 대출 ID, 처리 유형(`EXTEND`), 처리자(`SYSTEM`) 등이 포함됩니다.

7. **연장 이력 저장**  
   생성된 연장 이력 정보를 데이터베이스에 저장합니다 (`loanMapper.insertLoanHist` 호출).
- 관련 테이블: TB_BOOK, TB_LOAN, TB_LOAN_HIST, TB_MEMBER
- 참고: 처리 흐름 — LoanController.updateExtend → LoanServiceImpl.selectLoan → LoanServiceImpl.updateExtend → SQL 3건

### 도서 반납 처리
- 화면 경로: `/loan/updateReturn.do`
- 처리 절차:
1. **대출 정보 확인**  
   - 회원이 신청한 대출 ID를 입력합니다.
   - 시스템은 해당 대출 정보를 검색합니다 (`selectLoan` 메서드 호출).
   - 대출 정보가 존재하지 않으면 처리가 거부됩니다 (`DataNotFoundException` 발생).

2. **반납 처리**  
   - 현재 날짜를 반납일로 설정합니다 (`returnDate`).
   - 대출 정보의 상태를 '반납 완료'로 업데이트합니다 (`loan.setLoanStatus(LoanStatus.RETURNED.getCode())`).
   - 반납 처리를 데이터베이스에 반영합니다 (`loanMapper.updateReturn(loan)`).

3. **도서 대출 가능 상태 복원**  
   - 해당 도서의 대출 가능 상태를 'Y'(가능)로 변경하여 다시 대출 가능하도록 설정합니다 (`bookMapper.updateLoanYn(loan.getBookId(), "Y")`).

4. **연체 확인 및 처리**  
   - 반납일이 대출 만료일(`DueDate`)을 초과했는지 확인합니다.
   - 만약 연체가 발생했다면:
     - 연체 일수를 계산합니다 (`DateUtil.calcOverdueDays`).
     - 연체 정보를 생성하고 데이터베이스에 등록합니다 (`overdueMapper.insertOverdue`).
     - 연체 중인 회원의 대출 상태를 일시 정지로 변경합니다 (`memberMapper.updateMemberStatus`).

5. **반납 이력 기록**  
   - 반납 처리 이력을 생성합니다 (`LoanHistVO` 객체 생성).
   - 반납 처리 이력을 데이터베이스에 기록합니다 (`loanMapper.insertLoanHist`).
- 관련 테이블: TB_BOOK, TB_LOAN, TB_LOAN_HIST, TB_MEMBER, TB_OVERDUE
- 참고: 처리 흐름 — LoanController.updateReturn → LoanServiceImpl.selectLoan → LoanServiceImpl.updateReturn → SQL 6건

## 5. 연체 관리

### 연체 상태 일괄 갱신
- 화면 경로: `/overdue/refreshOverdueStatus.do`
- 처리 절차:
1. 입력된 검색 조건에 맞는 데이터를 조회합니다.
2. 조회된 결과를 반환합니다.
- 관련 테이블: TB_LOAN, TB_MEMBER, TB_OVERDUE
- 참고: 처리 흐름 — OverdueController.refreshOverdueStatus → OverdueServiceImpl.refreshOverdueStatus → SQL 6건

### 회원별 연체 이력 조회
- 화면 경로: `/overdue/selectOverdueByMember.do`
- 처리 절차:
1. 입력된 검색 조건에 맞는 데이터를 조회합니다.
2. 조회된 결과를 반환합니다.
- 관련 테이블: TB_BOOK, TB_LOAN, TB_MEMBER, TB_OVERDUE
- 참고: 처리 흐름 — OverdueController.selectOverdueByMember → OverdueServiceImpl.selectOverdueByMember → SQL 1건

### 연체 상세 조회
- 화면 경로: `/overdue/selectOverdueDetail.do`
- 처리 절차:
1. **요청 접수**: 연체 정보 조회 요청을 받습니다. 이 요청은 주로 사용자 ID나 연체 ID를 포함합니다.
2. **정보 검색**: 시스템은 `/overdue/selectOverdueDetail.do` 경로를 통해 연체 정보를 검색합니다.
3. **데이터 확인**: `OverdueServiceImpl.selectOverdue` 메서드를 통해 지정된 `overdueId`에 해당하는 연체 정보를 데이터베이스에서 조회합니다.
4. **결과 검증**: 
   - 만약 `overdueVO`가 `null`이면, 해당 연체 정보가 존재하지 않는 것으로 판단합니다.
   - 이 경우 `DataNotFoundException`이 발생하여 처리가 중단됩니다. 메시지는 "연체 정보를 찾을 수 없습니다. overdueId=[입력된 overdueId]" 입니다.
5. **정보 반환**: 연체 정보가 존재하면, 해당 정보를 포함한 `OverdueVO` 객체를 반환하여 다음 단계의 처리에 사용합니다.
- 관련 테이블: TB_BOOK, TB_LOAN, TB_MEMBER, TB_OVERDUE
- 참고: 처리 흐름 — OverdueController.selectOverdueDetail → OverdueServiceImpl.selectOverdue → SQL 1건

### 연체자 목록 조회
- 화면 경로: `/overdue/selectOverdueList.do`
- 처리 절차:
1. 입력된 검색 조건에 맞는 데이터를 조회합니다.
2. 조회된 결과를 반환합니다.
- 관련 테이블: TB_BOOK, TB_LOAN, TB_MEMBER, TB_OVERDUE
- 참고: 처리 흐름 — OverdueController.selectOverdueList → OverdueServiceImpl.selectOverdueList → OverdueServiceImpl.selectOverdueListCount → SQL 2건

### 연체 해제 처리
- 화면 경로: `/overdue/updateRelease.do`
- 처리 절차:
1. **연체 건 선택**: 연체 관리 시스템에서 특정 연체 건 ID를 입력합니다.
2. **연체 정보 확인**: 선택된 연체 건 ID에 해당하는 연체 정보를 시스템에서 검색합니다.
   - 만약 연체 정보가 존재하지 않으면 처리가 중단되고 오류 메시지 ("연체 정보를 찾을 수 없습니다. overdueId=[입력된 ID]")가 표시됩니다.
3. **해제 상태 확인**: 연체 정보의 현재 해제 상태를 확인합니다.
   - 이미 해제된 상태(코드: `RELEASED`)인 경우 처리가 거부되고 오류 메시지 ("이미 해제 처리된 연체 건입니다.")가 표시됩니다.
4. **연체 해제 처리**: 연체 정보의 해제 상태를 업데이트합니다.
   - `releaseDate` 필드에 현재 날짜를 기록합니다.
   - `sanctionStatus` 필드를 해제 상태(코드: `RELEASED`)로 변경합니다.
5. **데이터베이스 업데이트**: 변경된 연체 정보를 데이터베이스에 반영합니다.
6. **회원 상태 복원**: 연체 해제와 연계된 대출 정보를 조회합니다.
   - 대출 정보의 회원 ID를 기반으로 회원 상태를 정상 상태(코드: `NORMAL`)로 업데이트합니다.
- 관련 테이블: TB_BOOK, TB_LOAN, TB_MEMBER, TB_OVERDUE
- 참고: 처리 흐름 — OverdueController.updateRelease → OverdueServiceImpl.selectOverdue → OverdueServiceImpl.updateRelease → SQL 4건

## 6. 부록: 테이블 정의서

### TB_BOOK — 도서 정보 테이블. LOAN_YN은 대출 처리 시 N, 반납 처리 시 Y로 변경됨

| 컬럼 | 타입 | PK | NULL 허용 | 설명 |
|---|---|---|---|---|
| BOOK_ID | VARCHAR(20) | O | X | 도서ID. 시스템 발급 고유키 |
| ISBN | VARCHAR(20) |  | X | ISBN. 13자리 국제표준도서번호 |
| TITLE | VARCHAR(200) |  | X | 서명(도서 제목) |
| AUTHOR | VARCHAR(100) |  | X | 저자명 |
| PUBLISHER | VARCHAR(100) |  | O | 출판사명 |
| PUBLISH_DATE | DATE |  | O | 출판일 |
| CATEGORY_CD | VARCHAR(10) |  | O | 분류코드. TB_CATEGORY 참조 |
| LOCATION | VARCHAR(50) |  | O | 소장위치. 예: 2층 자료실 A-3 |
| LOAN_YN | CHAR(1) |  | X | 대출가능여부. Y=대출가능, N=대출중(다른 회원이 대출 중) |
| REG_DATE | DATETIME |  | X | 등록일시 |

### TB_CATEGORY — 도서 분류 코드 테이블. 계층형 분류 체계(상위분류코드로 자기참조)

| 컬럼 | 타입 | PK | NULL 허용 | 설명 |
|---|---|---|---|---|
| CATEGORY_CD | VARCHAR(10) | O | X | 분류코드. 예: 000(총류),100(철학) 등 KDC 대분류 스타일 |
| CATEGORY_NM | VARCHAR(100) |  | X | 분류명 |
| UPPER_CATEGORY_CD | VARCHAR(10) |  | O | 상위분류코드. 최상위 분류는 NULL |

### TB_LOAN — 대출 정보 테이블. 1인 최대 5권까지 동시 대출 가능(LOAN_STATUS=1 건수 기준)

| 컬럼 | 타입 | PK | NULL 허용 | 설명 |
|---|---|---|---|---|
| LOAN_ID | VARCHAR(20) | O | X | 대출ID. 시스템 발급 고유키 |
| BOOK_ID | VARCHAR(20) |  | X | 도서ID. TB_BOOK 참조 |
| MEMBER_ID | VARCHAR(20) |  | X | 회원ID. TB_MEMBER 참조 |
| LOAN_DATE | DATE |  | X | 대출일 |
| DUE_DATE | DATE |  | X | 반납예정일. 대출일+14일이 기본값, 연장 시 +7일씩 연장 |
| RETURN_DATE | DATE |  | O | 실제반납일. 반납 완료 전에는 NULL |
| LOAN_STATUS | CHAR(1) |  | X | 대출상태. 1=대출중, 2=반납완료, 3=연체중(반납예정일 경과 & 미반납) |
| EXTEND_CNT | INT |  | X | 연장횟수. 1회당 반납예정일 7일 연장 |

### TB_LOAN_HIST — 대출 처리 이력 테이블. 대출/반납/연장 처리마다 1건씩 적재되는 감사 로그

| 컬럼 | 타입 | PK | NULL 허용 | 설명 |
|---|---|---|---|---|
| HIST_ID | VARCHAR(20) | O | X | 이력ID. 시스템 발급 고유키 |
| LOAN_ID | VARCHAR(20) |  | X | 대출ID. TB_LOAN 참조 |
| PROCESS_TYPE | CHAR(1) |  | X | 처리유형. 1=대출, 2=반납, 3=연장 |
| PROCESS_DATETIME | DATETIME |  | X | 처리일시 |
| PROCESSOR | VARCHAR(50) |  | O | 처리자. 담당 사서ID 또는 SYSTEM(자동처리) |

### TB_MEMBER — 회원 정보 테이블. MEMBER_STATUS=2(대출정지)인 회원은 신규 대출 불가

| 컬럼 | 타입 | PK | NULL 허용 | 설명 |
|---|---|---|---|---|
| MEMBER_ID | VARCHAR(20) | O | X | 회원ID. 시스템 발급 고유키 |
| MEMBER_NM | VARCHAR(50) |  | X | 회원 이름 |
| BIRTH_DATE | DATE |  | O | 생년월일 |
| PHONE | VARCHAR(20) |  | O | 연락처 |
| EMAIL | VARCHAR(100) |  | O | 이메일 |
| MEMBER_STATUS | CHAR(1) |  | X | 회원상태. 1=정상, 2=대출정지(연체 제재 중), 9=탈퇴 |
| JOIN_DATE | DATE |  | X | 가입일 |

### TB_OVERDUE — 연체 정보 테이블. 연체 발생 시 회원의 MEMBER_STATUS가 2(대출정지)로 변경됨

| 컬럼 | 타입 | PK | NULL 허용 | 설명 |
|---|---|---|---|---|
| OVERDUE_ID | VARCHAR(20) | O | X | 연체ID. 시스템 발급 고유키 |
| LOAN_ID | VARCHAR(20) |  | X | 대출ID. TB_LOAN 참조 |
| OVERDUE_START_DATE | DATE |  | X | 연체시작일. 반납예정일 다음날 |
| OVERDUE_DAYS | INT |  | X | 연체일수. 반납일(또는 조회시점)-반납예정일 |
| RELEASE_DATE | DATE |  | O | 연체해제일. 제재 해제 처리일. 처리 전에는 NULL |
| SANCTION_STATUS | CHAR(1) |  | X | 제재상태. 1=제재중(대출정지), 2=해제됨 |