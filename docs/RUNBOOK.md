# 실행 가이드 (RUNBOOK)

이 문서 하나로 전체 시스템(AI 분석 어시스턴트 + 분석 대상 도서관 사이트)을 기동/테스트할 수
있습니다. 처음 보는 사람도 따라 할 수 있도록 명령어를 그대로 적었습니다.

## 전체 구성 한눈에 보기

| 서비스 | 포트 | 역할 | 이 프로젝트에서의 위치 |
|---|---|---|---|
| Ollama | 11434 | 로컬 LLM(EXAONE 3.5) 서빙 | 별도 설치된 앱, 프로젝트 밖 |
| MariaDB | 3307 | 도서관 데이터(library_db) | `C:\Program Files\MariaDB 12.3` |
| FastAPI | 8000 | AI 분석 API (Q&A/진단/SQL/매뉴얼) | `server/` |
| Streamlit | 8501 | AI 분석 어시스턴트 화면 | `ui/app.py` |
| **Tomcat** | **8080** | **도서관 사이트(진짜 웹앱)** | `C:\Users\gunny\tools\apache-tomcat-9.0.120` (프로젝트 밖) |

**Tomcat/도서관 사이트는 AI 분석 어시스턴트 데모에 필수가 아닙니다.** 5분 시연 시나리오
(`target-system/demo/scenario.md`)는 Streamlit(8501)만으로 완결됩니다. Tomcat은 "분석 대상
시스템이 실제로 어떻게 동작하는지 직접 보여주고 싶을 때"를 위한 보너스입니다.

---

## 1. AI 분석 어시스턴트 실행 (핵심, 데모용)

### 사전 조건
- Ollama 앱이 켜져 있어야 함 (트레이 아이콘 확인, 또는 `ollama list`로 `exaone3.5:7.8b` 확인)

### 한 번에 실행
탐색기에서 `scripts\run_all.bat` 더블클릭. 자동으로:
1. Ollama 응답 확인
2. MariaDB(3307) 확인 → 꺼져 있으면 자동 기동
3. FastAPI 새 창에서 기동 (`localhost:8000`)
4. `/health` 응답 대기
5. Streamlit 새 창에서 기동 (`localhost:8501`)

완료되면 브라우저에서 **http://localhost:8501** 접속.

> **주의**: 배치 파일은 줄바꿈이 CRLF여야 정상 동작합니다(LF만 있으면 cmd 창이 뜨자마자
> 조용히 닫힘 — 2026-08-14에 실제로 겪은 문제, 지금은 고쳐져 있습니다). 혹시 이 파일을 다시
> 수정하게 되면 저장 시 줄바꿈 형식을 CRLF로 유지하세요.

### 수동으로 단계별 실행 (run_all.bat이 안 될 때)
```
:: 1) MariaDB (꺼져 있을 때만)
powershell -Command "Start-Process -FilePath 'C:\Program Files\MariaDB 12.3\bin\mariadbd.exe' -ArgumentList '--defaults-file=\"C:\Program Files\MariaDB 12.3\data\my.ini\"' -WindowStyle Hidden"

:: 2) FastAPI
.venv\Scripts\activate.bat
uvicorn server.main:app --host 127.0.0.1 --port 8000

:: 3) Streamlit (새 창에서)
.venv\Scripts\activate.bat
streamlit run ui\app.py
```

### 종료
`run_all.bat`이 띄운 "FastAPI"·"Streamlit" 창을 닫으면 됩니다. MariaDB는 창이 없는 백그라운드
프로세스라 작업관리자에서 `mariadbd.exe`를 종료하거나 컴퓨터 재부팅 시 같이 꺼집니다.

---

## 2. 도서관 사이트(target-system) 실행 — Tomcat

target-system은 원래 "AI가 분석할 소스코드"로만 만들어져서 실행 설정이 없었습니다.
2026-08-15에 직접 띄워보면서 Tomcat 9를 새로 설치하고, 그 과정에서 발견된 실배포 버그
(Mapper/Service 빈 이름 충돌)도 고쳤습니다.

### 사전 준비 (최초 1회, 이미 완료됨)
- Tomcat 9.0.120이 `C:\Users\gunny\tools\apache-tomcat-9.0.120`에 설치돼 있음
  (Tomcat 10 이상은 안 됨 — 이 프로젝트가 옛날 방식인 `javax.servlet` API를 쓰기 때문에
  Tomcat 9까지만 호환됨)
- Java 17 (`C:\Program Files\Eclipse Adoptium\jdk-17.0.20.8-hotspot`)로 구동 확인됨
- DB 접속: `src/main/resources/db.properties`에 `root`/비밀번호 없음으로 설정돼 있고,
  로컬 MariaDB(3307)의 root 계정이 실제로 비밀번호가 없어서 그대로 동작함
  (AI 시스템이 쓰는 읽기전용 `ai_reader` 계정과는 다른 별개의 계정입니다 — 헷갈리지 마세요)

### 기동
```
:: 1) MariaDB가 켜져 있어야 함 (위 1번 항목 참고)

:: 2) Tomcat 기동 (PowerShell 권장 — cmd에서 이상하게 안 되는 경우가 있었음)
$env:JAVA_HOME = "C:\Program Files\Eclipse Adoptium\jdk-17.0.20.8-hotspot"
$env:CATALINA_HOME = "C:\Users\gunny\tools\apache-tomcat-9.0.120"
& "$env:CATALINA_HOME\bin\catalina.bat" run
```
이 창은 로그를 계속 찍으면서 떠 있어야 합니다(포그라운드 실행). 창을 닫으면 Tomcat도 꺼집니다.
백그라운드로 띄우고 싶으면 `startup.bat`을 대신 더블클릭해도 되지만(새 창에서 실행), 안 되면
위 PowerShell 방법을 쓰세요.

기동 후 **http://localhost:8080/book/selectBookList.do** 접속하면 도서 목록 화면이 뜹니다.

### 전체 URL 목록
`target-system/README.md`의 "URL 목록" 절에 22개 URL 전부 정리돼 있습니다. 대표적으로:
- `/book/selectBookList.do` — 도서 목록
- `/member/selectMemberList.do` — 회원 목록
- `/loan/selectLoanList.do` — 대출 목록
- `/overdue/selectOverdueList.do` — 연체 목록

### 종료
`catalina.bat run` 창을 그냥 닫거나 Ctrl+C. 또는:
```
$env:CATALINA_HOME = "C:\Users\gunny\tools\apache-tomcat-9.0.120"
& "$env:CATALINA_HOME\bin\shutdown.bat"
```

### target-system 소스를 고친 뒤 다시 반영하는 법
Java 코드나 `root-context.xml` 등을 수정했다면:
```
cd target-system
./mvnw package                         # WAR 다시 빌드
:: Tomcat이 켜져 있으면 먼저 종료
copy /Y target\library-system.war "C:\Users\gunny\tools\apache-tomcat-9.0.120\webapps\ROOT.war"
:: 위 "기동" 절차로 Tomcat 다시 시작
```
그리고 **AI 시스템의 인덱스도 같이 최신화**하세요 (Streamlit [시스템 분석] 탭의 재인덱싱
버튼, 또는 `POST /api/index/start`) — 소스 라인 번호가 바뀌면 Q&A/진단 답변의 근거 라인도
같이 갱신해야 정확합니다.

### 겪었던 문제와 원인 (참고용)
Tomcat에 처음 배포했을 때 `ConflictingBeanDefinitionException`으로 배포가 실패했습니다.
MyBatis의 Mapper 자동 스캔(`MapperScannerConfigurer`)이 `egovframework.library` 패키지
전체를 훑으면서, 같은 패키지에 있는 `BookService` 같은 **Service 인터페이스까지 매퍼로
착각**해 스프링 빈 이름이 충돌한 것이었습니다. `BookMapper`/`LoanMapper`/`MemberMapper`/
`OverdueMapper` 4개 인터페이스에 `@Mapper` 어노테이션을 붙이고, `root-context.xml`의 스캐너
설정에 `annotationClass` 필터를 추가해 해결했습니다(`[D12] target-system 실배포 시 발견된
Spring 빈 충돌 버그 수정` 커밋). `BUGS.md`에 적힌 시연용 의도적 버그 2개와는 무관한, 앱을
한 번도 실행해본 적이 없어서 여태 발견되지 않았던 버그입니다.

---

## 3. 화면에서 테스트하기

### AI 분석 어시스턴트 (http://localhost:8501)
| 탭 | 확인할 것 |
|---|---|
| 시스템 분석 | 통계 카드 표시 확인 |
| 프로세스 Q&A | 예시 질문 버튼 → 답변 + 근거 코드 expander |
| 장애 진단 | 샘플 로그 불러오기 → line 63 짚어내는지 |
| SQL 질의 | 예시 질문 → SQL+결과 표 / 위험 질문 → 차단 메시지 |
| 업무 매뉴얼 | 도메인 생성 또는 최근 생성본 불러오기 |

정확히 어떤 질문을 눌러야 검증된 결과가 나오는지는 `target-system/demo/scenario.md` 참고.

### 도서관 사이트 (http://localhost:8080)
목록/상세/등록 화면이 정상적으로 뜨는지, 검색 폼이 동작하는지 눈으로 확인.

---

## 4. 명령줄로 테스트하기

```
:: 파서/그래프/검색 로직 스모크 테스트 (24개, 수십 초)
.venv\Scripts\pytest tests\ -q

:: 시연 질문 반복 안정성 재검증 (113회 API 호출, 30~40분 — 결과 파일을 덮어쓰니 필요할 때만)
.venv\Scripts\python.exe scripts\demo_test.py
```

---

## 5. 문제 해결 (자주 겪은 문제)

| 증상 | 원인 | 해결 |
|---|---|---|
| `run_all.bat` 더블클릭 시 창이 뜨자마자 사라짐 | 배치 파일 줄바꿈이 LF만 있음 | CRLF로 재저장 (2026-08-14에 이미 고침) |
| SQL 질의 탭이 "연결 실패" | MariaDB(3307)가 꺼져 있음 | `run_all.bat` 재실행하거나 위 1번 MariaDB 기동 명령 실행 |
| 사이드바가 "로컬 AI 연결 실패" | Ollama가 꺼져 있음 | Ollama 앱 실행 |
| Tomcat 배포 시 `ConflictingBeanDefinitionException` | 이미 고쳐진 버그(위 참고) | 최신 커밋 기준이면 발생 안 함 |
| Tomcat이 `cmd /c`로는 조용히 안 뜨는데 더블클릭하면 될 때 | 자동화 도구(비대화형 셸)에서만 나타나는 콘솔 생성 문제로 추정 | PowerShell로 `catalina.bat run` 직접 실행 권장 |
| 컴퓨터 재부팅 후 아무것도 안 뜸 | MariaDB/Tomcat 둘 다 Windows 서비스가 아니라 매번 수동 기동 필요 | 위 1번, 2번 기동 절차 다시 실행 |

---

## 부록: 접속 정보 모음

| 항목 | 값 |
|---|---|
| Streamlit (AI 어시스턴트) | http://localhost:8501 |
| FastAPI (AI API) | http://localhost:8000 (`/health`로 상태 확인) |
| 도서관 사이트 (Tomcat) | http://localhost:8080 |
| Ollama | http://localhost:11434 |
| MariaDB | 127.0.0.1:3307, DB `library_db` |
| MariaDB 계정 (AI, 읽기전용) | `ai_reader` / `server/config.py` 또는 `.env` 참고 |
| MariaDB 계정 (도서관 사이트, 읽기쓰기) | `root` / 비밀번호 없음 |
| Tomcat 설치 위치 | `C:\Users\gunny\tools\apache-tomcat-9.0.120` (git 저장소 밖) |
