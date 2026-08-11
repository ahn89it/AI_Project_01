"""청킹 → e5 임베딩 → ChromaDB 적재 파이프라인.

입력: D4의 data/parsed/java_symbols.json, mapper_sqls.json
      D5의 data/graph.db (하류 테이블 역채움 + node_id 조인키 소스)
출력: data/chroma/ 의 "code_chunks" 컬렉션

청킹 규약
    - 대상: CONTROLLER/SERVICE_IMPL 메서드 전부, Mapper XML의 SQL(1 SQL = 1청크)
    - 제외: VO 전체, Service 인터페이스(구현체와 중복), Mapper 인터페이스 메서드 자체
      (실제 내용은 SQL 청크가 담당) — 이는 java_symbols.json의 layer 필터만으로 자연히 걸러짐
    - 임베딩 텍스트 = "설명 헤더 + ---  + 코드/SQL 원문"
    - "관련 테이블"은 graph.db에서 해당 노드의 하류(outgoing edge)를 따라가 도달하는
      TABLE 노드를 역채움한다 (한국어 질문에 테이블명이 없어도 업무 맥락 매칭이 되도록)
    - 메서드 바로 위 한국어 주석이 있으면 "주석:" 줄을 넣고, 없으면 그 줄 자체를 생략

메타데이터 (ChromaDB에 저장, node_id는 graph.db 노드ID와 반드시 동일한 문자열)
    node_id, layer, class_name, method_name, file_path, start_line, end_line, url, tables

실행 방식:
    python -m analyzer.indexer
    → 기존 "code_chunks" 컬렉션 삭제 후 재생성 (멱등성)
"""
from __future__ import annotations

import argparse
import json
import logging
import sqlite3
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from server.config import (
    CHROMA_DIR,
    GRAPH_DB_PATH,
    JAVA_SYMBOLS_JSON,
    MAPPER_SQLS_JSON,
    TARGET_SYSTEM_DIR,
)
from server.services.embedding import get_embedding_service

logger = logging.getLogger(__name__)

COLLECTION_NAME = "code_chunks"
_LAYER_LABEL = {"CONTROLLER": "Controller", "SERVICE_IMPL": "ServiceImpl"}

ProgressCallback = Callable[[int, int, str], None]


@dataclass
class Chunk:
    node_id: str
    layer: str  # CONTROLLER | SERVICE_IMPL | SQL
    class_name: Optional[str]
    method_name: Optional[str]
    file_path: str
    start_line: int
    end_line: int
    url: Optional[str]
    tables: list
    text: str


def _read_source_lines(file_path: str, start_line: int, end_line: int) -> str:
    full_path = TARGET_SYSTEM_DIR / file_path
    lines = full_path.read_text(encoding="utf-8").splitlines()
    return "\n".join(lines[start_line - 1:end_line])


def _downstream_tables(conn: sqlite3.Connection, node_id: str) -> list:
    from analyzer.callgraph import downstream_subgraph

    sub = downstream_subgraph(conn, node_id)
    tables = sorted({n["label"] for n in sub["nodes"] if n["node_type"] == "TABLE"})
    return tables


def _build_method_chunk(conn: sqlite3.Connection, class_info: dict, method_info: dict) -> Chunk:
    from analyzer.callgraph import method_node_id

    layer = class_info["layer"]
    node_id = method_node_id(class_info["class_name"], method_info["method_name"], layer)
    tables = _downstream_tables(conn, node_id)
    code = _read_source_lines(class_info["file_path"], method_info["start_line"], method_info["end_line"])

    header_lines = [
        f"계층: {_LAYER_LABEL[layer]} | 클래스: {class_info['class_name']} | 메서드: {method_info['method_name']}",
    ]
    if method_info.get("url"):
        header_lines.append(f"URL: {method_info['url']}")
    if method_info.get("leading_comment"):
        comment = method_info["leading_comment"].strip().strip("/*").strip()
        header_lines.append(f"주석: {comment}")
    if tables:
        header_lines.append(f"관련 테이블: {', '.join(tables)}")

    text = "\n".join(header_lines) + "\n---\n" + code

    return Chunk(
        node_id=node_id,
        layer=layer,
        class_name=class_info["class_name"],
        method_name=method_info["method_name"],
        file_path=class_info["file_path"],
        start_line=method_info["start_line"],
        end_line=method_info["end_line"],
        url=method_info.get("url"),
        tables=tables,
        text=text,
    )


def _build_sql_chunk(sql_info: dict) -> Chunk:
    from analyzer.callgraph import sql_node_id

    node_id = sql_node_id(sql_info["namespace"], sql_info["sql_id"])
    mapper_class = sql_info["namespace"].rsplit(".", 1)[-1]
    tables = sql_info["referenced_tables"]

    header_lines = [
        f"계층: SQL | Mapper: {mapper_class} | SQL ID: {sql_info['sql_id']}",
        f"유형: {sql_info['sql_type']}",
    ]
    if tables:
        header_lines.append(f"관련 테이블: {', '.join(tables)}")
    header_lines.append(f"XML 파일: {sql_info['file_path']}")

    text = "\n".join(header_lines) + "\n---\n" + sql_info["sql_text"]

    return Chunk(
        node_id=node_id,
        layer="SQL",
        class_name=mapper_class,
        method_name=sql_info["sql_id"],
        file_path=sql_info["file_path"],
        start_line=sql_info["start_line"],
        end_line=sql_info["end_line"],
        url=None,
        tables=tables,
        text=text,
    )


def build_chunks(classes: list, sqls: list, conn: sqlite3.Connection) -> list:
    chunks: list = []
    for c in classes:
        if c["layer"] not in ("CONTROLLER", "SERVICE_IMPL"):
            continue
        for m in c["methods"]:
            chunks.append(_build_method_chunk(conn, c, m))

    for s in sqls:
        chunks.append(_build_sql_chunk(s))

    return chunks


def _get_collection():
    import chromadb

    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass  # 최초 실행 시 컬렉션이 없을 수 있음
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


def index_chunks(chunks: list, batch_size: int = 16, progress: Optional[ProgressCallback] = None) -> None:
    collection = _get_collection()
    embedder = get_embedding_service()

    total = len(chunks)
    for i in range(0, total, batch_size):
        batch = chunks[i:i + batch_size]
        embeddings = embedder.embed_documents([c.text for c in batch], batch_size=batch_size)
        collection.add(
            ids=[c.node_id for c in batch],
            embeddings=embeddings,
            documents=[c.text for c in batch],
            metadatas=[{
                "node_id": c.node_id,
                "layer": c.layer,
                "class_name": c.class_name or "",
                "method_name": c.method_name or "",
                "file_path": c.file_path,
                "start_line": c.start_line,
                "end_line": c.end_line,
                "url": c.url or "",
                "tables": ",".join(c.tables),
            } for c in batch],
        )
        done = min(i + batch_size, total)
        if progress:
            progress(done, total, f"임베딩/적재 {done}/{total}")
        else:
            logger.info("임베딩/적재 진행: %d/%d", done, total)


def run(progress: Optional[ProgressCallback] = None) -> dict:
    if not JAVA_SYMBOLS_JSON.exists() or not MAPPER_SQLS_JSON.exists():
        raise FileNotFoundError("D4 산출물이 없습니다. analyzer.java_parser / mapper_parser 를 먼저 실행하세요.")
    if not GRAPH_DB_PATH.exists():
        raise FileNotFoundError("D5 산출물(graph.db)이 없습니다. analyzer.callgraph 를 먼저 실행하세요.")

    start = time.time()

    classes = json.loads(JAVA_SYMBOLS_JSON.read_text(encoding="utf-8"))
    sqls = json.loads(MAPPER_SQLS_JSON.read_text(encoding="utf-8"))

    conn = sqlite3.connect(GRAPH_DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        chunks = build_chunks(classes, sqls, conn)
    finally:
        conn.close()

    logger.info("청크 %d개 생성 완료. 임베딩/ChromaDB 적재 시작...", len(chunks))
    index_chunks(chunks, progress=progress)

    elapsed = time.time() - start
    layer_counts: dict = {}
    for c in chunks:
        layer_counts[c.layer] = layer_counts.get(c.layer, 0) + 1

    result = {"chunk_count": len(chunks), "layer_counts": layer_counts, "elapsed_sec": elapsed}
    logger.info("인덱싱 완료: 청크 %d개, %.1f초 소요, 계층별=%s", len(chunks), elapsed, layer_counts)
    return result


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s - %(message)s")
    parser = argparse.ArgumentParser(description="청킹 + 임베딩 + ChromaDB 인덱싱")
    parser.parse_args()

    try:
        from tqdm import tqdm
        bar = {"pbar": None}

        def on_progress(done: int, total: int, message: str) -> None:
            if bar["pbar"] is None:
                bar["pbar"] = tqdm(total=total, desc="indexing")
            bar["pbar"].n = done
            bar["pbar"].refresh()

        result = run(progress=on_progress)
        if bar["pbar"] is not None:
            bar["pbar"].close()

        print(f"청크 수: {result['chunk_count']}")
        print(f"계층별: {result['layer_counts']}")
        print(f"소요 시간: {result['elapsed_sec']:.1f}초")
    except Exception:
        logger.error("indexer 실행 실패", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
