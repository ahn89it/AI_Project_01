"""Streamlit UI — FastAPI(localhost:8000)를 호출하는 표시 계층.

이 파일에는 분석/AI 로직이 없다. 전부 requests로 FastAPI를 호출하고 결과를 렌더링만 한다.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

# `streamlit run ui/app.py`로 실행할 때도 프로젝트 루트를 import 경로에 포함시킨다
# (server.config 등을 그대로 재사용하기 위함 — 값 중복 금지).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import requests
import streamlit as st

from server.config import API_BASE_URL, DB_SCHEMA_SQL, JAVA_SRC_DIR, TARGET_SYSTEM_DIR

st.set_page_config(layout="wide", page_title="eGov Code Insight", page_icon="📚")

TIMEOUT = 180
SAMPLE_ERROR_LOG_PATH = TARGET_SYSTEM_DIR / "demo" / "error_log_1.txt"

QA_EXAMPLES = [
    "도서 대출은 어떻게 처리되나요?",
    "연체된 회원은 책을 빌릴 수 있나요?",
    "회원은 몇 권까지 빌릴 수 있나요?",
]
SQL_EXAMPLES = [
    "이번 달 연체 회원 목록과 연체 일수를 보여줘",
    "가장 많이 대출된 책 10권을 알려줘",
    "정지 상태인 회원 목록",
]
SQL_DANGEROUS_EXAMPLE = "회원 테이블을 전부 지워줘"

NAV_ITEMS = [
    ("🔍", "시스템 분석"),
    ("💬", "프로세스 Q&A"),
    ("🚨", "장애 진단"),
    ("🗄️", "SQL 질의"),
    ("📖", "업무 매뉴얼"),
]


# ---------------------------------------------------------------------------
# 스타일 (색상은 .streamlit/config.toml 테마를 그대로 따름 — 여기서는 레이아웃만 보정)
# ---------------------------------------------------------------------------

st.markdown(
    """
    <style>
    .page-header {
        display: flex; align-items: center; gap: 0.9rem;
        padding: 1rem 1.4rem; margin-bottom: 1.2rem; border-radius: 14px;
        background: linear-gradient(135deg, #1B4D89 0%, #2E6FB0 100%);
        color: #FFFFFF;
    }
    .page-header .icon { font-size: 2.1rem; line-height: 1; }
    .page-header .title { font-size: 1.35rem; font-weight: 700; margin: 0; }
    .page-header .caption { font-size: 0.92rem; opacity: 0.88; margin-top: 0.15rem; }
    section[data-testid="stSidebar"] .stRadio > label { display: none; }
    section[data-testid="stSidebar"] .stRadio div[role="radiogroup"] label {
        padding: 0.35rem 0.5rem; border-radius: 8px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def page_header(icon: str, title: str, caption: str) -> None:
    st.markdown(
        f"""
        <div class="page-header">
            <div class="icon">{icon}</div>
            <div>
                <p class="title">{title}</p>
                <p class="caption">{caption}</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# 공통 유틸
# ---------------------------------------------------------------------------

def call_api(method: str, path: str, **kwargs) -> "dict | None":
    """FastAPI 호출 공통 유틸. 연결 실패/타임아웃은 여기서 st.error로 처리하고 None을 반환한다.
    반환값이 있으면 {"ok": bool, "status_code": int, "data": dict} 형태."""
    url = f"{API_BASE_URL}{path}"
    try:
        resp = requests.request(method, url, timeout=TIMEOUT, **kwargs)
    except requests.exceptions.ConnectionError:
        st.error(
            "백엔드 서버(FastAPI)에 연결할 수 없습니다. "
            "`scripts/run_all`로 서버가 켜져 있는지 확인하세요. "
            f"(주소: {API_BASE_URL})"
        )
        return None
    except requests.exceptions.Timeout:
        st.error("응답이 시간 초과되었습니다. 잠시 후 다시 시도해주세요.")
        return None
    except Exception as e:
        st.error(f"요청 중 오류가 발생했습니다: {e}")
        return None

    if resp.status_code >= 500:
        st.error("서버에서 오류가 발생했습니다. 잠시 후 다시 시도해주세요.")
        return {"ok": False, "status_code": resp.status_code, "data": {}}

    try:
        data = resp.json()
    except Exception:
        st.error("서버 응답을 해석할 수 없습니다.")
        return None

    return {"ok": resp.status_code < 400, "status_code": resp.status_code, "data": data}


@st.cache_data(ttl=5)
def _health_check() -> dict:
    res = call_api("GET", "/health")
    if res and res["ok"]:
        return res["data"]
    return {"status": "down", "ollama_online": False, "llm_model": "-"}


def _load_sample_log() -> str:
    try:
        return SAMPLE_ERROR_LOG_PATH.read_text(encoding="utf-8")
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# 세션 상태 초기화
# ---------------------------------------------------------------------------

_DEFAULTS = {
    "chat_history": [],
    "pending_question": None,
    "diagnose_log": "",
    "diagnose_result": None,
    "sql_pending_question": None,
    "sql_result": None,
    "sql_blocked": None,
    "manual_md": None,
    "manual_generated_at": None,
    "reindex_stats": None,
    "nav": f"{NAV_ITEMS[0][0]}  {NAV_ITEMS[0][1]}",
}
for _k, _v in _DEFAULTS.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v


# ---------------------------------------------------------------------------
# 사이드바 — 메뉴(왼쪽 배치) + 상태
# ---------------------------------------------------------------------------

with st.sidebar:
    st.markdown("### 📚 eGov Code Insight")
    st.caption("폐쇄망 시스템 분석 AI 어시스턴트")
    st.divider()

    nav_labels = [f"{icon}  {label}" for icon, label in NAV_ITEMS]
    nav = st.radio("메뉴", nav_labels, key="nav", label_visibility="collapsed")

    st.divider()

    health = _health_check()
    if health.get("ollama_online"):
        st.success(f"외부 연결: 차단됨 / AI: 로컬 EXAONE 3.5\n\n모델: `{health.get('llm_model')}`")
    else:
        st.error("로컬 AI(Ollama) 연결 실패 — `ollama serve` 상태를 확인하세요.")

    st.subheader("분석 대상")
    st.text(f"경로: {TARGET_SYSTEM_DIR.name}/")

    stats_res = call_api("GET", "/api/index/stats")
    if stats_res and stats_res["ok"]:
        s = stats_res["data"]
        if s["indexed"]:
            st.markdown(
                f"- 클래스 **{s['class_count']}**개 · 메서드 **{s['method_count']}**개\n"
                f"- URL **{s['url_count']}**개 · SQL **{s['sql_count']}**개 · 테이블 **{s['table_count']}**개\n"
                f"- 인덱싱 청크 **{s['chunk_count']}**개"
            )
        else:
            st.warning("아직 인덱싱되지 않았습니다. [시스템 분석] 메뉴에서 분석을 시작하세요.")

    st.caption("전체 재인덱싱은 [시스템 분석] 메뉴에서 실행할 수 있습니다.")


# ---------------------------------------------------------------------------
# 페이지별 렌더링 함수
# ---------------------------------------------------------------------------

def render_dashboard() -> None:
    page_header("🔍", "시스템 분석", "소스코드를 정적 분석해 호출그래프와 벡터 인덱스를 만듭니다.")

    col1, col2 = st.columns(2)
    col1.text_input("소스 경로", value=str(JAVA_SRC_DIR), disabled=True)
    col2.text_input("DDL 경로", value=str(DB_SCHEMA_SQL), disabled=True)

    stats_res = call_api("GET", "/api/index/stats")
    if stats_res and stats_res["ok"]:
        s = stats_res["data"]
        with st.container(border=True):
            st.markdown("#### 현재 인덱싱 상태")
            m1, m2, m3, m4, m5, m6 = st.columns(6)
            m1.metric("클래스", s["class_count"])
            m2.metric("메서드", s["method_count"])
            m3.metric("URL", s["url_count"])
            m4.metric("SQL", s["sql_count"])
            m5.metric("테이블", s["table_count"])
            m6.metric("청크", s["chunk_count"])

    if st.session_state.reindex_stats:
        rs = st.session_state.reindex_stats
        with st.container(border=True):
            st.markdown("#### 최근 재인덱싱 결과")
            m1, m2, m3, m4, m5, m6 = st.columns(6)
            m1.metric("클래스", rs["class_count"])
            m2.metric("메서드", rs["method_count"])
            m3.metric("URL", rs["node_counts"].get("URL", 0))
            m4.metric("SQL", rs["sql_count"])
            m5.metric("테이블", rs["node_counts"].get("TABLE", 0))
            m6.metric("청크", rs["chunk_count"])
            st.caption(
                f"소요 시간: {rs.get('elapsed_sec', '-')}초 · "
                f"호출그래프 unresolved 비율: {rs.get('unresolved_ratio', 0) * 100:.1f}%"
            )

    st.divider()
    if st.button("🔄 전체 분석 시작 / 재인덱싱", type="primary"):
        start_res = call_api("POST", "/api/index/start")
        if start_res and start_res["ok"]:
            progress_bar = st.progress(0.0)
            status_box = st.empty()
            while True:
                status_res = call_api("GET", "/api/index/status")
                if not status_res or not status_res["ok"]:
                    st.error("진행 상태 조회에 실패했습니다.")
                    break
                d = status_res["data"]
                if d["status"] == "running":
                    total = max(d["total"], 1)
                    progress_bar.progress(min(d["current"] / total, 1.0))
                    status_box.info(f"**{d['stage']}** — {d['message']}")
                    time.sleep(1.2)
                elif d["status"] == "done":
                    progress_bar.progress(1.0)
                    status_box.success(f"인덱싱 완료 (소요 시간: {d['elapsed_sec']}초)")
                    st.session_state.reindex_stats = d["stats"]
                    st.rerun()
                elif d["status"] == "error":
                    status_box.error(f"인덱싱 실패: {d['error']}")
                    break
                else:
                    break
        elif start_res and not start_res["ok"]:
            st.warning(start_res["data"].get("detail", "이미 진행 중입니다."))


def render_qa() -> None:
    page_header("💬", "프로세스 Q&A", "업무 처리 절차를 한국어로 물어보세요. 답변은 실제 소스코드를 근거로 생성됩니다.")

    with st.container(border=True):
        st.markdown("**예시 질문**")
        ex_cols = st.columns(len(QA_EXAMPLES))
        for col, q in zip(ex_cols, QA_EXAMPLES):
            if col.button(q, key=f"qa_ex_{q}"):
                st.session_state.pending_question = q

    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg["role"] == "assistant":
                if msg.get("chain_summary"):
                    st.info(msg["chain_summary"])
                refs = msg.get("references") or []
                if refs:
                    with st.expander(f"근거 코드 {len(refs)}건"):
                        for r in refs:
                            st.markdown(f"**{r['file']}:{r['line_start']}-{r['line_end']}** — `{r['class_method']}`")
                            st.code(r["snippet"], language="java")
                if msg.get("elapsed_ms") is not None:
                    st.caption(f"응답 시간: {msg['elapsed_ms'] / 1000:.1f}초")

    user_input = st.chat_input("업무 프로세스에 대해 질문해보세요")
    question = user_input or st.session_state.pending_question
    if question:
        st.session_state.pending_question = None
        st.session_state.chat_history.append({"role": "user", "content": question})
        with st.spinner("로컬 AI가 코드를 분석 중입니다... (약 20~40초)"):
            res = call_api("POST", "/api/rag/ask", json={"question": question})
        if res and res["ok"]:
            data = res["data"]
            st.session_state.chat_history.append({
                "role": "assistant", "content": data["answer"],
                "chain_summary": data.get("chain_summary"), "references": data.get("references"),
                "elapsed_ms": data.get("elapsed_ms"),
            })
        elif res:
            st.session_state.chat_history.append({
                "role": "assistant",
                "content": f"답변 생성에 실패했습니다: {res['data'].get('detail', '알 수 없는 오류')}",
                "chain_summary": None, "references": [],
            })
        st.rerun()


def render_diagnose() -> None:
    page_header("🚨", "장애 진단", "에러 로그/스택트레이스를 붙여넣으면 문제 코드 위치와 수정안을 제시합니다.")

    def _fill_sample_log():
        st.session_state.diagnose_log = _load_sample_log()

    with st.container(border=True):
        col_a, col_b = st.columns([1, 1])
        col_a.button("📋 샘플 에러 로그 불러오기", on_click=_fill_sample_log)
        st.text_area("에러 로그를 붙여넣으세요", height=200, key="diagnose_log")

        if st.button("🔍 진단 시작", type="primary"):
            if not st.session_state.diagnose_log.strip():
                st.warning("에러 로그를 입력하거나 샘플을 불러와주세요.")
            else:
                with st.spinner("로컬 AI가 스택트레이스와 코드를 대조하는 중입니다... (약 15~40초)"):
                    res = call_api("POST", "/api/diagnose", json={"error_log": st.session_state.diagnose_log})
                st.session_state.diagnose_result = res

    res = st.session_state.diagnose_result
    if res is not None:
        if not res["ok"]:
            st.warning(f"진단할 수 없습니다: {res['data'].get('detail', '알 수 없는 오류')}")
        else:
            data = res["data"]
            with st.container(border=True):
                loc = data.get("error_location")
                if loc:
                    st.error(f"🚨 문제 위치: `{loc['file']}:{loc['line']}` — `{loc['class_method']}()`")
                if data.get("warning"):
                    st.warning(data["warning"])
                chain = data.get("call_chain") or []
                if chain:
                    st.info("처리 흐름: " + " → ".join(chain))
                st.markdown(data["diagnosis"])
                st.caption(f"응답 시간: {data['elapsed_ms'] / 1000:.1f}초")
                refs = data.get("references") or []
                if refs:
                    with st.expander(f"근거 코드 {len(refs)}건"):
                        for r in refs:
                            st.markdown(f"**{r['file']}:{r['line_start']}-{r['line_end']}** — `{r['class_method']}`")
                            st.code(r["snippet"], language="java")


def render_sql() -> None:
    page_header("🗄️", "SQL 질의 (Text-to-SQL)", "자연어로 물으면 SQL을 생성해 검증 후 읽기전용 계정으로 실행합니다.")

    with st.container(border=True):
        st.markdown("**예시 질문**")
        ex_cols = st.columns(len(SQL_EXAMPLES) + 1)
        for col, q in zip(ex_cols, SQL_EXAMPLES):
            if col.button(q, key=f"sql_ex_{q}"):
                st.session_state.sql_pending_question = q
        if ex_cols[-1].button(f"⚠️ {SQL_DANGEROUS_EXAMPLE}", key="sql_ex_danger"):
            st.session_state.sql_pending_question = SQL_DANGEROUS_EXAMPLE

        sql_question = st.text_input("질문을 입력하세요", key="sql_question_input")
        run_clicked = st.button("실행", type="primary", key="sql_run")

    question = None
    if run_clicked and sql_question.strip():
        question = sql_question.strip()
    elif st.session_state.sql_pending_question:
        question = st.session_state.sql_pending_question

    if question:
        st.session_state.sql_pending_question = None
        with st.spinner("SQL 생성 및 실행 중... (약 5~30초)"):
            res = call_api("POST", "/api/text2sql", json={"question": question})
        st.session_state.sql_result = {"question": question, "res": res}

    stored = st.session_state.sql_result
    if stored:
        with st.container(border=True):
            st.markdown(f"**질문**: {stored['question']}")
            res = stored["res"]
            if res is None:
                pass
            elif not res["ok"]:
                st.warning(f"🚫 요청이 차단되었습니다: {res['data'].get('detail', 'SELECT 이외의 구문은 차단됩니다.')}")
            else:
                data = res["data"]
                st.code(data["sql"], language="sql")
                if data.get("guard_notes"):
                    for note in data["guard_notes"]:
                        st.info(f"ℹ️ {note}")
                if data["columns"] and data["rows"]:
                    st.dataframe(
                        [dict(zip(data["columns"], row)) for row in data["rows"]],
                        use_container_width=True,
                    )
                else:
                    st.caption("조회 결과가 없습니다.")
                st.caption(
                    f"결과 {data['row_count']}건 · 응답 시간 {data['elapsed_ms'] / 1000:.1f}초"
                    + (" · 재시도 있었음" if data.get("retried") else "")
                )


def render_manual() -> None:
    page_header("📖", "업무 매뉴얼 자동 생성", "호출그래프의 URL 목록을 순회하며 도메인별 업무 처리 절차를 자동 문서화합니다.")

    domain_labels = {
        "all": "전체", "book": "도서 관리", "member": "회원 관리",
        "loan": "대출·반납", "overdue": "연체 관리",
    }
    with st.container(border=True):
        domain = st.selectbox(
            "도메인 선택", options=list(domain_labels.keys()),
            format_func=lambda k: domain_labels[k], index=3,  # 기본값: 대출·반납 (시연용)
        )

        col_a, col_b = st.columns(2)
        generate_clicked = col_a.button("📝 매뉴얼 생성", type="primary")
        load_latest_clicked = col_b.button("📂 최근 생성본 불러오기 (백업본)")

    if generate_clicked:
        with st.spinner(f"'{domain_labels[domain]}' 도메인 매뉴얼 생성 중... (URL당 약 10~30초)"):
            res = call_api("POST", "/api/manual/generate", json={"domain": domain})
        if res and res["ok"]:
            st.session_state.manual_md = res["data"]["manual_md"]
            st.session_state.manual_generated_at = res["data"]["generated_at"]
            st.success(
                f"생성 완료 (URL {res['data']['url_count']}개, "
                f"{res['data']['elapsed_ms'] / 1000:.1f}초)"
            )
        elif res:
            st.error(res["data"].get("detail", "매뉴얼 생성에 실패했습니다."))

    if load_latest_clicked:
        res = call_api("GET", "/api/manual/latest")
        if res and res["ok"]:
            st.session_state.manual_md = res["data"]["manual_md"]
            st.session_state.manual_generated_at = res["data"]["generated_at"]
        elif res:
            st.warning(res["data"].get("detail", "아직 생성된 매뉴얼이 없습니다."))

    if st.session_state.manual_md:
        with st.container(border=True):
            st.caption(f"생성일시: {st.session_state.manual_generated_at}")
            st.download_button(
                "⬇️ Markdown 다운로드", data=st.session_state.manual_md,
                file_name="library_manual.md", mime="text/markdown",
            )
            st.markdown(st.session_state.manual_md)


# ---------------------------------------------------------------------------
# 라우팅 — 왼쪽 사이드바에서 고른 메뉴에 맞는 페이지 렌더링
# ---------------------------------------------------------------------------

_ROUTES = [render_dashboard, render_qa, render_diagnose, render_sql, render_manual]
_selected_index = nav_labels.index(nav)
_ROUTES[_selected_index]()
