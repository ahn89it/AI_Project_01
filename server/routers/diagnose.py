"""장애 진단 API. POST /api/diagnose"""
from __future__ import annotations

import logging
import time
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from server.services.context_builder import build_diagnose_context
from server.services.llm import OllamaConnectionError, chat
from server.services.prompts import DIAGNOSE_SYSTEM_PROMPT, build_diagnose_user_prompt
from server.services.stacktrace_parser import NotAStackTraceError, parse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["diagnose"])


class DiagnoseRequest(BaseModel):
    error_log: str


class ReferenceOut(BaseModel):
    file: str
    line_start: int
    line_end: int
    class_method: str
    snippet: str


class DiagnoseResponse(BaseModel):
    diagnosis: str
    error_location: Optional[dict]
    call_chain: list
    references: list
    elapsed_ms: int
    warning: Optional[str] = None


@router.post("/diagnose", response_model=DiagnoseResponse)
def diagnose(req: DiagnoseRequest) -> DiagnoseResponse:
    start = time.time()

    try:
        parsed = parse(req.error_log)
    except NotAStackTraceError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    ctx = build_diagnose_context(parsed)

    if not ctx.found:
        elapsed_ms = int((time.time() - start) * 1000)
        return DiagnoseResponse(
            diagnosis=(
                "이 에러 로그에서 자체 시스템(egovframework.library) 코드 프레임을 찾을 수 없습니다. "
                "프레임워크/라이브러리 내부에서 발생한 오류이거나, 우리 코드가 관여하지 않는 예외로 보입니다. "
                "우리 코드가 포함된 스택트레이스를 다시 확인해 주세요."
            ),
            error_location=None, call_chain=[], references=[], elapsed_ms=elapsed_ms,
        )

    user_prompt = build_diagnose_user_prompt(req.error_log, ctx.text)
    try:
        diagnosis = chat(DIAGNOSE_SYSTEM_PROMPT, user_prompt, temperature=0.2)
    except OllamaConnectionError as e:
        logger.error("LLM 호출 실패: %s", e)
        raise HTTPException(status_code=503, detail=str(e)) from e

    elapsed_ms = int((time.time() - start) * 1000)

    warning_parts = []
    if ctx.fallback_used:
        warning_parts.append("정확한 위치 특정 실패, 유사 코드 기준 분석입니다.")
    if ctx.line_mismatch_warning:
        warning_parts.append(ctx.line_mismatch_warning)
    warning = " ".join(warning_parts) if warning_parts else None

    references = [
        ReferenceOut(
            file=r.file, line_start=r.line_start, line_end=r.line_end,
            class_method=r.class_method, snippet=r.snippet,
        ).model_dump()
        for r in ctx.references
    ]

    return DiagnoseResponse(
        diagnosis=diagnosis,
        error_location=ctx.error_location,
        call_chain=ctx.call_chain,
        references=references,
        elapsed_ms=elapsed_ms,
        warning=warning,
    )
