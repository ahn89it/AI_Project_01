"""업무 매뉴얼 생성 API.

POST /api/manual/generate {"domain": "loan" | "all" | ...}
GET  /api/manual/latest   — 가장 최근 생성본 반환 (시연 백업본 표시용)
"""
from __future__ import annotations

import logging
import time

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from server.services.manual_builder import MANUALS_DIR, generate_manual

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/manual", tags=["manual"])


class ManualGenerateRequest(BaseModel):
    domain: str = "all"


class ManualGenerateResponse(BaseModel):
    manual_md: str
    generated_at: str
    elapsed_ms: int
    url_count: int


@router.post("/generate", response_model=ManualGenerateResponse)
def generate(req: ManualGenerateRequest) -> ManualGenerateResponse:
    start = time.time()
    try:
        result = generate_manual(domain=req.domain)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    elapsed_ms = int((time.time() - start) * 1000)

    MANUALS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = result["generated_at"].replace(":", "").replace("-", "").replace(".", "_")
    out_path = MANUALS_DIR / f"manual_{timestamp}.md"
    out_path.write_text(result["manual_md"], encoding="utf-8")
    logger.info("매뉴얼 저장 완료: %s", out_path)

    return ManualGenerateResponse(
        manual_md=result["manual_md"], generated_at=result["generated_at"],
        elapsed_ms=elapsed_ms, url_count=result["url_count"],
    )


@router.get("/latest", response_model=ManualGenerateResponse)
def latest() -> ManualGenerateResponse:
    if not MANUALS_DIR.exists():
        raise HTTPException(status_code=404, detail="아직 생성된 매뉴얼이 없습니다.")

    files = sorted(MANUALS_DIR.glob("manual_*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not files:
        raise HTTPException(status_code=404, detail="아직 생성된 매뉴얼이 없습니다.")

    latest_file = files[0]
    manual_md = latest_file.read_text(encoding="utf-8")
    generated_at = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(latest_file.stat().st_mtime))

    # "### " 헤더는 기능 섹션과 부록의 테이블 섹션 모두에 쓰이므로, 부록(## 6.) 이전 부분만 센다.
    body_before_appendix = manual_md.split("## 6. 부록", 1)[0]

    return ManualGenerateResponse(
        manual_md=manual_md, generated_at=generated_at, elapsed_ms=0,
        url_count=body_before_appendix.count("### "),
    )
