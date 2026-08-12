"""시스템 프로세스 Q&A API. POST /api/rag/ask"""
from __future__ import annotations

import logging
import time

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from server.services.context_builder import build_context
from server.services.llm import OllamaConnectionError, chat
from server.services.prompts import RAG_SYSTEM_PROMPT, build_user_prompt

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/rag", tags=["rag"])


class AskRequest(BaseModel):
    question: str


class ReferenceOut(BaseModel):
    file: str
    line_start: int
    line_end: int
    class_method: str
    snippet: str


class AskResponse(BaseModel):
    answer: str
    references: list
    chain_summary: str
    elapsed_ms: int


@router.post("/ask", response_model=AskResponse)
def ask(req: AskRequest) -> AskResponse:
    start = time.time()

    context = build_context(req.question)
    user_prompt = build_user_prompt(req.question, context.text)

    try:
        answer = chat(RAG_SYSTEM_PROMPT, user_prompt, temperature=0.2)
    except OllamaConnectionError as e:
        logger.error("LLM 호출 실패: %s", e)
        raise HTTPException(status_code=503, detail=str(e)) from e

    elapsed_ms = int((time.time() - start) * 1000)

    # references는 LLM 출력에서 파싱하지 않는다 — context_builder가 실제로 프롬프트에
    # 넣은 코드 기준이므로 이 목록 자체가 사실이다.
    references = [
        ReferenceOut(
            file=r.file, line_start=r.line_start, line_end=r.line_end,
            class_method=r.class_method, snippet=r.snippet,
        ).model_dump()
        for r in context.references
    ]

    return AskResponse(
        answer=answer,
        references=references,
        chain_summary=context.chain_summary,
        elapsed_ms=elapsed_ms,
    )
