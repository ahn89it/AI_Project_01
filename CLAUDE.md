
markdown
# CLAUDE.md 

## 프로젝트 개요

**폐쇄망 시스템 분석 AI 어시스턴트 **
공공기관 AI 서비스 대회 출품용 프로토타입.

외부 인터넷이 차단된 공공기관 폐쇄망 안에서, 국산 로컬 sLLM(EXAONE)이
전자정부프레임워크(eGovFrame) 기반 시스템의 소스코드와 DB를 분석하여:

1. **시스템 프로세스 Q&A** — 업무 처리 흐름 질의응답 (근거 코드 인용)
2. **장애 진단** — 에러 로그/스택트레이스 분석 → 문제 코드 위치 + 수정안 제시
3. **Text-to-SQL** — 자연어 요청 → SQL 생성 → 검증 → 실행 결과 표시
4. **업무 매뉴얼 자동 생성** — 호출그래프 순회 → Markdown 매뉴얼

**절대 원칙: 100% 오프라인 동작.** 외부 API 호출 코드는 절대 작성하지 않는다.
(OpenAI, Anthropic, Google 등 외부 LLM API 금지. 모든 AI는 로컬 Ollama 경유)

## 마감

- **오늘 기준 D-Day 일정: 2026-08-11(D1) ~ 2026-08-23(D13), 8/24 제출**
- 일정이 촉박하므로 "동작하는 최소 구현 → 커밋 → 개선" 사이클을 지킨다.
- 완벽한 코드보다 **오늘의 완료 기준 달성**이 우선이다.

## 기술 스택 (확정 — 변경 제안 금지)

| 구분 | 기술 | 비고 |
|---|---|---|
| 메인 LLM | **EXAONE 3.5 7.8B** (Q4, Ollama) | GPU(RTX 4060 8GB) 실행. 중국 모델(Qwen/BGE 계열) 사용 금지 |
| 임베딩 | **multilingual-e5-large** | CPU 실행 (VRAM 절약) |
| 모델 서빙 | Ollama (http://localhost:11434) | |
| 백엔드 | Python 3.11+, FastAPI | |
| UI | Streamlit | |
| 벡터 DB | ChromaDB (로컬 persist) | |
| 메타데이터/그래프 | SQLite | 호출그래프, 심볼 테이블 |
| 대상 시스템 DB | MariaDB | 읽기전용 계정으로 SQL 실행 |
| Java 파싱 | tree-sitter, tree-sitter-java | |
| SQL 검증 | sqlglot | SELECT만 허용 |
| 분석 대상 | Java (eGovFrame 4.x 스타일) + MyBatis Mapper XML + DDL | |

## 프로젝트 구조

```
AI_Project_01/
├── CLAUDE.md              # 이 파일
├── target-system/         # 분석 대상: eGov 스타일 도서관 시스템 (D2~D3 생성)
│   ├── src/main/java/egovframework/library/...
│   ├── src/main/resources/mappers/   # MyBatis Mapper XML
│   └── db/                # DDL(한글 코멘트 필수), 시딩 SQL
├── analyzer/              # 정적 분석 엔진 (배치 실행)
│   ├── java_parser.py     # Tree-sitter로 클래스/메서드/어노테이션 추출
│   ├── mapper_parser.py   # Mapper XML에서 SQL id/구문/테이블 추출
│   ├── ddl_parser.py      # DDL → 스키마 카탈로그(테이블/컬럼/코멘트/FK)
│   ├── callgraph.py       # URL→Controller→Service→DAO→SQL→테이블 그래프
│   └── indexer.py         # 청킹 → e5 임베딩 → ChromaDB 적재
├── server/                # FastAPI
│   ├── main.py
│   ├── routers/           # rag.py, diagnose.py, text2sql.py, manual.py, index.py
│   ├── services/          # llm.py(Ollama 클라이언트), retriever.py, prompts.py
│   └── config.py          # 경로/모델명/DB 접속 등 설정은 반드시 여기로
├── ui/
│   └── app.py             # Streamlit (탭: 채팅/장애진단/SQL/매뉴얼 + 인덱싱)
├── scripts/               # 인덱싱 배치 실행, 데이터 시딩
├── data/                  # ChromaDB persist, SQLite 파일 (git 제외)
└── tests/                 # 핵심 로직 스모크 테스트
```

## 아키텍처 핵심 개념 (모든 기능 구현 시 이 원칙을 따를 것)

### 호출그래프 기반 RAG (일반 RAG와 다름)

eGovFrame은 계층이 정형화되어 있다:
`@Controller(URL) → @Service/ServiceImpl → DAO/Mapper 인터페이스 → Mapper XML SQL → DB 테이블`

이 규칙성을 이용해 **정적 분석으로 "URL 단위 실행 흐름 그래프"를 먼저 구축**하고,
질의 시에는:

1. 벡터 검색으로 관련 메서드 청크를 찾는다 (진입점 탐색)
2. **호출그래프를 따라 상하류 코드를 확장 수집**한다 (Controller~SQL~테이블 전체 체인)
3. 수집한 실제 코드만 컨텍스트로 LLM에 주입한다
4. 답변에는 반드시 `파일경로:라인번호` 근거를 인용한다

이유: 7.8B 모델의 추론력 한계를 그래프가 보완하고 할루시네이션을 차단한다.
**LLM에게 "기억"으로 답하게 하지 말고, 항상 수집된 코드를 근거로 답하게 한다.**

### LLM 사용 원칙

- 모든 LLM 호출은 `server/services/llm.py` 한 곳으로 통일 (Ollama REST)
- 프롬프트 템플릿은 `server/services/prompts.py`에 상수로 모아둔다 (인라인 금지)
- 시스템 프롬프트는 한국어로 작성, 출력 형식을 명시적으로 강제한다
- 컨텍스트는 8K 토큰 이내로 유지 (초과 시 그래프 체인 우선, 주변 코드부터 자른다)

### 기능별 구현 규약

**① 인덱싱** (`analyzer/`, `server/routers/index.py`)
- 청킹 단위: 메서드 (메타데이터: 계층구분, 클래스명, 파일경로, 시작/끝 라인)
- getter/setter/단순 주석은 청킹 제외
- UI에 진행률 표시할 수 있도록 진행 상태 콜백/폴링 제공

**② Q&A** (`server/routers/rag.py`)
- 벡터 검색 top-5 → 그래프 확장 → 답변 생성
- 응답 JSON: `{ answer, references: [{file, line_start, line_end, snippet}] }`

**③ 장애 진단** (`server/routers/diagnose.py`)
- 정규식으로 스택트레이스 파싱: `at ([\w.$]+)\.(\w+)\(([\w]+\.java):(\d+)\)`
- 파싱된 심볼을 SQLite 심볼 테이블과 매핑 → 해당 메서드 + 호출 체인 코드 수집
- 출력 4단 구조 강제: **원인 분석 → 문제 코드 위치 → 수정 코드 제안 → 재발 방지**

**④ Text-to-SQL** (`server/routers/text2sql.py`) — EXAONE 약점 보완 구역
- 프롬프트 구성: 스키마 카탈로그(한글 코멘트 포함) + **few-shot 4~5개**
  (few-shot은 Mapper XML의 실제 SQL 중 유사한 것을 벡터 검색으로 선택)
- 생성 SQL은 sqlglot으로 파싱 → **SELECT 외 전부 거부** (INSERT/UPDATE/DELETE/DDL 차단)
- MariaDB 읽기전용 계정으로 실행, LIMIT 100 강제, 결과를 그리드용 JSON으로 반환

**⑤ 매뉴얼 생성** (`server/routers/manual.py`) — 우선순위 최하
- 호출그래프에서 URL 목록 추출 → 기능별 흐름 순회 → LLM 단계 설명 → Markdown 조립
- 구조: 목차 / 기능별(개요, 처리 절차, 관련 화면 URL, 관련 테이블)

## 대상 시스템 (target-system/) 생성 규약 — D2~D3

- eGovFrame 4.x 경량환경 스타일: `Controller / Service / ServiceImpl / Mapper(인터페이스) / Mapper XML / VO`
- 패키지: `egovframework.library.{book,member,loan,overdue}`
- 도메인: 도서 관리, 회원 관리, 대출/반납, 연체 관리 — 테이블 6개 내외
- **DDL의 모든 테이블/컬럼에 한글 COMMENT 필수** (Text-to-SQL 품질 직결)
- 더미 데이터 수백 건 시딩 (연체 데이터는 "이번 달" 기준으로 존재하도록)
- **의도적 버그 2개 삽입** (시연용, 위치를 README에 기록):
  1. LoanServiceImpl: 회원 조회 결과 NULL 체크 누락 → NPE 발생 가능
  2. 대출 등록 시 중복 대출 체크 누락 → 데이터 정합성 버그

## 코딩 규칙

- 언어: Python 3.11+, 타입 힌트 사용, 함수는 짧게
- 설정값(경로, 모델명, DB 접속 정보)은 하드코딩 금지 → `server/config.py` + `.env`
- 주석/문서/커밋 메시지/LLM 프롬프트는 한국어
- 에러는 삼키지 말고 로그 남기기 (logging 모듈, print 금지)
- 외부 네트워크 호출 금지 (localhost Ollama/MariaDB 제외). pip 패키지는 requirements.txt에 고정
- 각 기능 완성 시마다 git 커밋 (메시지: `[D7] RAG Q&A 기본 동작 구현` 형식)
- 테스트: pytest 스모크 테스트 최소한만 (파서 출력 형태, SQL 


───


이 CLAUDE.md의 설계 의도
• "변경 제안 금지" 명시 — Claude Code는 종종 "더 좋은 모델/라이브러리"를 제안하며 옆길로 새는데, 13일 일정에서 이를 차단합니다
• 비전공자 배려 지시 포함 — 마지막 "작업 방식" 섹션 덕분에 Claude Code가 코드마다 설명을 달아줘서, 바이브코딩 자체가 Just-in-Time 학습이 됩니다
• V2 금지 목록 명시 — 리랭커·BM25 등을 Claude Code가 임의로 추가하지 않도록 못 박았습니다
• 일자별 완료 기준 내장 — 매일 "오늘 D5 작업 해줘"라고만 해도 Claude Code가 목표를 알고 움직입니다
• 응답 JSON 형식·정규식·출력 4단 구조까지 규약화 — 세션이 바뀌어도 일관된 구현이 나오도록 구체화했습니다
다음으로 필요하시면 D2용 도서관 시스템 생성 상세 프롬프트(테이블 설계, 버그 삽입 위치 포함)를 준비해 드리겠습니다. 오늘은 우선 Ollama 설치와 EXAONE 다운로드부터 진행하세요.