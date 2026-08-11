-- ================================================================
-- 도서관 관리 시스템 스키마 (target-system/db/schema.sql)
-- 대상: MariaDB
-- 모든 테이블/컬럼에 한글 COMMENT 포함 (Text-to-SQL 품질에 직결)
-- ================================================================

CREATE DATABASE IF NOT EXISTS library_db DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;
USE library_db;

DROP TABLE IF EXISTS TB_LOAN_HIST;
DROP TABLE IF EXISTS TB_OVERDUE;
DROP TABLE IF EXISTS TB_LOAN;
DROP TABLE IF EXISTS TB_BOOK;
DROP TABLE IF EXISTS TB_MEMBER;
DROP TABLE IF EXISTS TB_CATEGORY;

CREATE TABLE TB_CATEGORY (
    CATEGORY_CD         VARCHAR(10)   NOT NULL COMMENT '분류코드. 예: 000(총류),100(철학) 등 KDC 대분류 스타일',
    CATEGORY_NM          VARCHAR(100)  NOT NULL COMMENT '분류명',
    UPPER_CATEGORY_CD     VARCHAR(10)            COMMENT '상위분류코드. 최상위 분류는 NULL',
    PRIMARY KEY (CATEGORY_CD),
    CONSTRAINT FK_CATEGORY_UPPER FOREIGN KEY (UPPER_CATEGORY_CD) REFERENCES TB_CATEGORY (CATEGORY_CD)
) COMMENT='도서 분류 코드 테이블. 계층형 분류 체계(상위분류코드로 자기참조)';

CREATE TABLE TB_BOOK (
    BOOK_ID       VARCHAR(20)   NOT NULL COMMENT '도서ID. 시스템 발급 고유키',
    ISBN          VARCHAR(20)   NOT NULL COMMENT 'ISBN. 13자리 국제표준도서번호',
    TITLE         VARCHAR(200)  NOT NULL COMMENT '서명(도서 제목)',
    AUTHOR        VARCHAR(100)  NOT NULL COMMENT '저자명',
    PUBLISHER     VARCHAR(100)           COMMENT '출판사명',
    PUBLISH_DATE  DATE                   COMMENT '출판일',
    CATEGORY_CD   VARCHAR(10)            COMMENT '분류코드. TB_CATEGORY 참조',
    LOCATION      VARCHAR(50)            COMMENT '소장위치. 예: 2층 자료실 A-3',
    LOAN_YN       CHAR(1)       NOT NULL DEFAULT 'Y' COMMENT '대출가능여부. Y=대출가능, N=대출중(다른 회원이 대출 중)',
    REG_DATE      DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '등록일시',
    PRIMARY KEY (BOOK_ID),
    CONSTRAINT FK_BOOK_CATEGORY FOREIGN KEY (CATEGORY_CD) REFERENCES TB_CATEGORY (CATEGORY_CD)
) COMMENT='도서 정보 테이블. LOAN_YN은 대출 처리 시 N, 반납 처리 시 Y로 변경됨';

CREATE TABLE TB_MEMBER (
    MEMBER_ID      VARCHAR(20)  NOT NULL COMMENT '회원ID. 시스템 발급 고유키',
    MEMBER_NM      VARCHAR(50)  NOT NULL COMMENT '회원 이름',
    BIRTH_DATE     DATE                  COMMENT '생년월일',
    PHONE          VARCHAR(20)           COMMENT '연락처',
    EMAIL          VARCHAR(100)          COMMENT '이메일',
    MEMBER_STATUS  CHAR(1)      NOT NULL DEFAULT '1' COMMENT '회원상태. 1=정상, 2=대출정지(연체 제재 중), 9=탈퇴',
    JOIN_DATE      DATE         NOT NULL COMMENT '가입일',
    PRIMARY KEY (MEMBER_ID)
) COMMENT='회원 정보 테이블. MEMBER_STATUS=2(대출정지)인 회원은 신규 대출 불가';

CREATE TABLE TB_LOAN (
    LOAN_ID      VARCHAR(20)  NOT NULL COMMENT '대출ID. 시스템 발급 고유키',
    BOOK_ID      VARCHAR(20)  NOT NULL COMMENT '도서ID. TB_BOOK 참조',
    MEMBER_ID    VARCHAR(20)  NOT NULL COMMENT '회원ID. TB_MEMBER 참조',
    LOAN_DATE    DATE         NOT NULL COMMENT '대출일',
    DUE_DATE     DATE         NOT NULL COMMENT '반납예정일. 대출일+14일이 기본값, 연장 시 +7일씩 연장',
    RETURN_DATE  DATE                  COMMENT '실제반납일. 반납 완료 전에는 NULL',
    LOAN_STATUS  CHAR(1)      NOT NULL DEFAULT '1' COMMENT '대출상태. 1=대출중, 2=반납완료, 3=연체중(반납예정일 경과 & 미반납)',
    EXTEND_CNT   INT          NOT NULL DEFAULT 0 COMMENT '연장횟수. 1회당 반납예정일 7일 연장',
    PRIMARY KEY (LOAN_ID),
    CONSTRAINT FK_LOAN_BOOK FOREIGN KEY (BOOK_ID) REFERENCES TB_BOOK (BOOK_ID),
    CONSTRAINT FK_LOAN_MEMBER FOREIGN KEY (MEMBER_ID) REFERENCES TB_MEMBER (MEMBER_ID)
) COMMENT='대출 정보 테이블. 1인 최대 5권까지 동시 대출 가능(LOAN_STATUS=1 건수 기준)';

CREATE TABLE TB_OVERDUE (
    OVERDUE_ID          VARCHAR(20)  NOT NULL COMMENT '연체ID. 시스템 발급 고유키',
    LOAN_ID             VARCHAR(20)  NOT NULL COMMENT '대출ID. TB_LOAN 참조',
    OVERDUE_START_DATE  DATE         NOT NULL COMMENT '연체시작일. 반납예정일 다음날',
    OVERDUE_DAYS        INT          NOT NULL DEFAULT 0 COMMENT '연체일수. 반납일(또는 조회시점)-반납예정일',
    RELEASE_DATE        DATE                  COMMENT '연체해제일. 제재 해제 처리일. 처리 전에는 NULL',
    SANCTION_STATUS     CHAR(1)      NOT NULL DEFAULT '1' COMMENT '제재상태. 1=제재중(대출정지), 2=해제됨',
    PRIMARY KEY (OVERDUE_ID),
    CONSTRAINT FK_OVERDUE_LOAN FOREIGN KEY (LOAN_ID) REFERENCES TB_LOAN (LOAN_ID)
) COMMENT='연체 정보 테이블. 연체 발생 시 회원의 MEMBER_STATUS가 2(대출정지)로 변경됨';

CREATE TABLE TB_LOAN_HIST (
    HIST_ID           VARCHAR(20)  NOT NULL COMMENT '이력ID. 시스템 발급 고유키',
    LOAN_ID           VARCHAR(20)  NOT NULL COMMENT '대출ID. TB_LOAN 참조',
    PROCESS_TYPE      CHAR(1)      NOT NULL COMMENT '처리유형. 1=대출, 2=반납, 3=연장',
    PROCESS_DATETIME  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '처리일시',
    PROCESSOR         VARCHAR(50)           COMMENT '처리자. 담당 사서ID 또는 SYSTEM(자동처리)',
    PRIMARY KEY (HIST_ID),
    CONSTRAINT FK_HIST_LOAN FOREIGN KEY (LOAN_ID) REFERENCES TB_LOAN (LOAN_ID)
) COMMENT='대출 처리 이력 테이블. 대출/반납/연장 처리마다 1건씩 적재되는 감사 로그';
