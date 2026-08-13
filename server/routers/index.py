"""분석 파이프라인(파싱→그래프→인덱싱) 실행 래퍼 API.

analyzer/의 각 모듈은 배치 스크립트로 설계돼 있어(`python -m analyzer.xxx`) 원래 동기
실행이다. Streamlit이 진행률을 폴링할 수 있도록, 백그라운드 스레드에서 파이프라인을 돌리고
그 진행 상태를 메모리에 들고 있다가 GET으로 조회하게 해주는 얇은 래퍼일 뿐 — 여기 자체에는
분석 로직이 없다(전부 analyzer/ 모듈 호출).
"""
from __future__ import annotations

import json
import logging
import sqlite3
import threading
import time
from typing import Optional

from fastapi import APIRouter, HTTPException

from analyzer.indexer import COLLECTION_NAME
from server.config import CHROMA_DIR, GRAPH_DB_PATH, JAVA_SYMBOLS_JSON, MAPPER_SQLS_JSON

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/index", tags=["index"])

_lock = threading.Lock()
_state: dict = {
    "status": "idle",  # idle | running | done | error
    "stage": "",
    "current": 0,
    "total": 1,
    "message": "",
    "elapsed_sec": None,
    "stats": None,
    "error": None,
}


def _set_state(**kwargs) -> None:
    with _lock:
        _state.update(kwargs)


def _run_pipeline() -> None:
    # analyzer 모듈은 여기서만 import한다 (요청마다 새로 로딩되지 않도록 스레드 시작 시점에 import)
    from analyzer import callgraph, indexer, java_parser, mapper_parser

    start = time.time()
    try:
        _set_state(status="running", stage="Java 소스 파싱", current=0, total=1,
                    message="Java 소스 파싱 중...", error=None)
        classes = java_parser.run()

        _set_state(stage="Mapper XML 파싱", message="Mapper XML 파싱 중...")
        sqls = mapper_parser.run()

        _set_state(stage="호출그래프 구축", message="호출그래프/스키마 카탈로그 구축 중...")
        graph_result = callgraph.run()

        _set_state(stage="임베딩/인덱싱", current=0, total=1, message="청킹 준비 중...")

        def _progress(done: int, total: int, message: str) -> None:
            _set_state(current=done, total=total, message=message)

        index_result = indexer.run(progress=_progress)

        elapsed = time.time() - start
        stats = {
            "class_count": len(classes),
            "method_count": sum(len(c.methods) for c in classes),
            "sql_count": len(sqls),
            "node_counts": graph_result["node_counts"],
            "edge_counts": graph_result["edge_counts"],
            "unresolved_ratio": graph_result["unresolved_ratio"],
            "chunk_count": index_result["chunk_count"],
        }
        _set_state(status="done", stage="완료", current=1, total=1,
                    message="인덱싱 완료", elapsed_sec=round(elapsed, 1), stats=stats)
        logger.info("전체 인덱싱 파이프라인 완료: %.1f초", elapsed)
    except Exception as e:
        logger.error("인덱싱 파이프라인 실패", exc_info=True)
        _set_state(status="error", error=str(e))


@router.post("/start")
def start_index() -> dict:
    with _lock:
        if _state["status"] == "running":
            raise HTTPException(status_code=409, detail="이미 인덱싱이 진행 중입니다.")
        _state.update(status="running", stage="대기", current=0, total=1,
                       message="시작 준비 중...", error=None, stats=None, elapsed_sec=None)

    thread = threading.Thread(target=_run_pipeline, daemon=True)
    thread.start()
    return {"status": "started"}


@router.get("/status")
def get_status() -> dict:
    with _lock:
        return dict(_state)


@router.get("/stats")
def get_stats() -> dict:
    """지금까지 인덱싱된 결과 통계 (파이프라인을 새로 돌리지 않고 기존 산출물만 조회)."""
    stats = {
        "class_count": 0, "method_count": 0, "url_count": 0,
        "sql_count": 0, "table_count": 0, "chunk_count": 0, "indexed": False,
    }

    try:
        if JAVA_SYMBOLS_JSON.exists():
            classes = json.loads(JAVA_SYMBOLS_JSON.read_text(encoding="utf-8"))
            stats["class_count"] = len(classes)
            stats["method_count"] = sum(len(c.get("methods", [])) for c in classes)
        if MAPPER_SQLS_JSON.exists() and stats["sql_count"] == 0:
            sqls = json.loads(MAPPER_SQLS_JSON.read_text(encoding="utf-8"))
            stats["sql_count"] = len(sqls)
        if GRAPH_DB_PATH.exists():
            conn = sqlite3.connect(GRAPH_DB_PATH)
            try:
                stats["url_count"] = conn.execute(
                    "SELECT COUNT(*) FROM nodes WHERE node_type='URL'").fetchone()[0]
                stats["table_count"] = conn.execute(
                    "SELECT COUNT(*) FROM nodes WHERE node_type='TABLE'").fetchone()[0]
            finally:
                conn.close()
        if CHROMA_DIR.exists():
            try:
                import chromadb
                client = chromadb.PersistentClient(path=str(CHROMA_DIR))
                collection = client.get_collection(COLLECTION_NAME)
                stats["chunk_count"] = collection.count()
            except Exception:
                pass
    except Exception:
        logger.warning("인덱싱 통계 조회 중 일부 실패", exc_info=True)

    stats["indexed"] = stats["class_count"] > 0 and stats["chunk_count"] > 0
    return stats
