"""ChromaDB(code_chunks) 검색 서비스. D7 RAG Q&A의 입구.

analyzer/indexer.py가 적재한 컬렉션을 e5 "query: " 접두사로 검색한다.
반환되는 Hit.node_id는 data/graph.db의 노드ID와 동일한 문자열이므로,
호출자는 이 값으로 analyzer.callgraph.expand()/get_chain() 등을 바로 이어 쓸 수 있다
(벡터 검색으로 진입점을 찾고 → 그래프로 상하류를 확장하는 구조의 조인 키).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from server.config import CHROMA_DIR
from server.services.embedding import get_embedding_service
from analyzer.indexer import COLLECTION_NAME


@dataclass
class Hit:
    node_id: str
    score: float
    metadata: dict
    text: str


def _get_collection():
    import chromadb

    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    return client.get_collection(COLLECTION_NAME)


def search(query: str, top_k: int = 5, layer_filter: Optional[str] = None) -> list:
    """한국어(또는 영어) 자연어 질의로 관련 코드/SQL 청크를 검색한다.

    Args:
        query: 자연어 질의 (e5 규약에 맞춰 내부에서 "query: " 접두사를 붙인다)
        top_k: 반환할 결과 개수
        layer_filter: "CONTROLLER" | "SERVICE_IMPL" | "SQL" 중 하나로 제한 (None이면 전체)
    """
    collection = _get_collection()
    embedder = get_embedding_service()
    query_embedding = embedder.embed_query(query)

    where = {"layer": layer_filter} if layer_filter else None
    result = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        where=where,
    )

    hits = []
    ids = result["ids"][0]
    distances = result["distances"][0]
    metadatas = result["metadatas"][0]
    documents = result["documents"][0]

    for node_id, distance, metadata, document in zip(ids, distances, metadatas, documents):
        hits.append(Hit(
            node_id=node_id,
            score=1.0 - distance,  # cosine distance -> 유사도 점수 (높을수록 유사)
            metadata=metadata,
            text=document,
        ))

    return hits
