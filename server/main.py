"""FastAPI 앱 진입점."""
import logging

from fastapi import FastAPI

from server.routers import diagnose, rag, text2sql

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s - %(message)s")

app = FastAPI(title="폐쇄망 시스템 분석 AI 어시스턴트")
app.include_router(rag.router)
app.include_router(diagnose.router)
app.include_router(text2sql.router)


@app.get("/health")
def health():
    return {"status": "ok"}
