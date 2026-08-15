# 도서관 관리 시스템 (target-system)

**본 프로젝트는 실제 운영용 시스템이 아니라, AI 분석 어시스턴트(analyzer/RAG)의 분석 대상 샘플 코드입니다.**
eGovFrame 4.x 경량환경 스타일(Spring MVC + MyBatis)로 작성되었으며, 화면 완성도보다 계층 구조의
정형성과 업무 의미가 코드에 잘 드러나는 것을 우선했습니다.

## 기술 스택

- Java 8, Spring Framework 5.3 (eGovFrame 4.x 경량환경 스타일 — 패키지/어노테이션 관례를 따르되
  실제 eGovFrame 런타임 의존성 대신 순수 Spring MVC로 구성)
- MyBatis 3.5 + mybatis-spring
- MariaDB (개발 환경: 로컬 3307 포트)
- Maven (Maven Wrapper 포함, `./mvnw`로 시스템에 Maven 미설치 상태에서도 빌드 가능)

## 빌드 / 실행

```bash
# 컴파일
./mvnw compile

# DB 스키마 생성 (MariaDB, 최초 1회)
mariadb -u root -P 3307 -h 127.0.0.1 < db/schema.sql
mariadb -u root -P 3307 -h 127.0.0.1 library_db < db/seed.sql

# WAR 빌드
./mvnw package
```

DB 접속 정보는 `src/main/resources/db.properties`에 있습니다 (로컬 개발용 기본값: root / 비밀번호 없음).

### 실제로 띄우기 (Tomcat 9)

WAR까지만 만들면 끝이던 걸 2026-08-15에 실제로 배포까지 검증했습니다. 서블릿 API가
`javax.servlet` 4.0(구버전 네임스페이스)이라 **Tomcat 9까지만** 호환됩니다(Tomcat 10+는
`jakarta.servlet`으로 바뀌어서 안 됨). 전체 절차와 트러블슈팅은
[`../docs/RUNBOOK.md`](../docs/RUNBOOK.md)의 "2. 도서관 사이트(target-system) 실행" 절 참고.

배포해보면서 발견한 버그(시연용 의도적 버그 2개와는 무관): `MapperScannerConfigurer`가
Service 인터페이스까지 매퍼로 오인해 스프링 빈 이름이 충돌하던 문제를 `@Mapper` 어노테이션 +
`annotationClass` 필터로 수정함.

## 패키지 구조

```
egovframework.library.book     - 도서 관리 (도서 분류 포함)
egovframework.library.member   - 회원 관리
egovframework.library.loan     - 대출/반납/연장 (핵심 업무 로직)
egovframework.library.overdue  - 연체 관리
egovframework.library.cmmn     - 공통 (예외, VO, 페이징/날짜 유틸)
```

각 도메인은 `Controller / Service / ServiceImpl / Mapper / VO` 5계층 구조를 따릅니다.

## URL 목록

### book (도서 관리)
| URL | Method | 설명 |
|---|---|---|
| /book/selectBookList.do | GET | 목록 조회 (서명/저자/분류/대출가능여부 검색) |
| /book/selectBookDetail.do | GET | 상세 조회 (JSON) |
| /book/selectCategoryList.do | GET | 분류 목록 조회 (JSON) |
| /book/insertBook.do | POST | 등록 |
| /book/updateBook.do | POST | 수정 |
| /book/deleteBook.do | POST | 삭제 |

### member (회원 관리)
| URL | Method | 설명 |
|---|---|---|
| /member/selectMemberList.do | GET | 목록 조회 |
| /member/selectMemberDetail.do | GET | 상세 조회 (JSON) |
| /member/insertMember.do | POST | 등록 |
| /member/updateMember.do | POST | 수정 |
| /member/deleteMember.do | POST | 삭제 |

### loan (대출/반납)
| URL | Method | 설명 |
|---|---|---|
| /loan/selectLoanList.do | GET | 목록 조회 |
| /loan/selectLoanDetail.do | GET | 상세 조회 (JSON) |
| /loan/checkLoanable.do | GET | 대출 가능 여부 사전 확인 (JSON, AJAX) |
| /loan/insertLoan.do | POST | 대출 등록 |
| /loan/updateReturn.do | POST | 반납 처리 |
| /loan/updateExtend.do | POST | 연장 처리 |

### overdue (연체 관리)
| URL | Method | 설명 |
|---|---|---|
| /overdue/selectOverdueList.do | GET | 연체자 목록 (TB_OVERDUE+TB_LOAN+TB_MEMBER+TB_BOOK 조인) |
| /overdue/selectOverdueDetail.do | GET | 상세 조회 (JSON) |
| /overdue/selectOverdueByMember.do | GET | 특정 회원 연체 이력 (JSON) |
| /overdue/updateRelease.do | POST | 연체 해제 처리 |
| /overdue/refreshOverdueStatus.do | POST | 연체 상태 일괄 갱신 배치 트리거 |

## 테이블 목록 (db/schema.sql)

| 테이블 | 설명 |
|---|---|
| TB_CATEGORY | 도서 분류 코드 (계층형, 상위분류코드로 자기참조) |
| TB_BOOK | 도서 정보 |
| TB_MEMBER | 회원 정보 |
| TB_LOAN | 대출 정보 |
| TB_OVERDUE | 연체 정보 |
| TB_LOAN_HIST | 대출 처리 이력 (대출/반납/연장 감사 로그) |

모든 테이블/컬럼에 한글 COMMENT가 포함되어 있습니다 (Text-to-SQL 근거 자료).

## 업무 규칙 요약

- **대출**: 1인 최대 5권, 대출 기간 14일 (`LibraryConstants.MAX_LOAN_COUNT`, `LOAN_PERIOD_DAYS`)
- **연체 중인 회원(MEMBER_STATUS=2)은 신규 대출 불가**
- 대출 시: `TB_BOOK.LOAN_YN` → 'N', `TB_LOAN` 등록, `TB_LOAN_HIST`에 이력 기록
- 반납 시: 대출가능여부 'Y'로 복원. 반납예정일 초과 시 `TB_OVERDUE` 등록 + 회원 대출정지(MEMBER_STATUS=2)
- 연장 시: 반납예정일 +7일 (`LibraryConstants.EXTEND_PERIOD_DAYS`), `EXTEND_CNT` 증가
- 연체 해제 시: `SANCTION_STATUS`를 해제로 변경하고 회원상태를 정상으로 복원
- 배치(`/overdue/refreshOverdueStatus.do`): 반납예정일이 지났지만 아직 반납/연체등록이 안 된 대출 건을
  연체로 전환하고, 이미 연체 중인 건들의 연체일수를 오늘 날짜 기준으로 재계산

## 의도적으로 삽입된 버그 (시연용)

장애 진단 기능 데모를 위해 아래 2개의 버그를 의도적으로 남겨두었습니다.

1. **NPE 가능 버그** — [`LoanServiceImpl.insertLoan()`](src/main/java/egovframework/library/loan/LoanServiceImpl.java)
   회원 조회 결과(`memberMapper.selectMember(...)`)에 대한 null 체크 없이 바로
   `member.getMemberStatus()`를 호출합니다. 존재하지 않는 `memberId`로 대출을 시도하면
   `NullPointerException`이 발생합니다. (참고: 같은 클래스의 `checkLoanable()`은 정상적으로
   null 체크를 하고 있어, 두 메서드 간 검증 수준이 다른 전형적인 패턴을 보여줍니다.)

2. **데이터 정합성 버그** — [`LoanServiceImpl.insertLoan()`](src/main/java/egovframework/library/loan/LoanServiceImpl.java)
   대출 대상 도서를 `bookMapper.selectBook(...)`으로 조회하지만, 조회된 `book.getLoanYn()` 값을
   검증하는 조건문이 없습니다. 따라서 이미 대출 중(`LOAN_YN='N'`)인 도서도 중복으로 대출 등록이
   가능하여 데이터 정합성이 깨질 수 있습니다.

## 참고

- JSP 화면은 최소한(도메인별 목록 1개씩)으로만 구성했습니다. 상세/등록/수정은 AJAX(JSON) 또는
  폼 POST 후 목록으로 리다이렉트하는 방식입니다.
- 개발 환경에는 MariaDB가 기본 포트(3306) 대신 3307에서 실행 중입니다 (해당 머신에 기존
  MySQL80 서비스가 3306을 사용 중이라 충돌 방지를 위해 분리, 자세한 내용은
  `../progress/D2.md` 참고).
