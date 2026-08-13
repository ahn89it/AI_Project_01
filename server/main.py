"""FastAPI 앱 진입점."""
import logging

import httpx
from fastapi import FastAPI

from server.config import LLM_MODEL, OLLAMA_HOST
from server.routers import diagnose, index, manual, rag, text2sql

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s - %(message)s")

app = FastAPI(title="폐쇄망 시스템 분석 AI 어시스턴트")
app.include_router(rag.router)
app.include_router(diagnose.router)
app.include_router(text2sql.router)
app.include_router(manual.router)
app.include_router(index.router)


@app.get("/health")
def health():
    """UI 사이드바의 '오프라인/로컬 AI' 상태 표시가 사용하는 헬스체크.
    Ollama가 실제로 떠 있는지까지 확인한다 (분석 로직 아님, 순수 인프라 상태 확인)."""
    ollama_online = False
    try:
        resp = httpx.get(f"{OLLAMA_HOST}/api/tags", timeout=3.0)
        ollama_online = resp.status_code == 200
    except Exception:
        ollama_online = False

    return {"status": "ok", "ollama_online": ollama_online, "llm_model": LLM_MODEL}
