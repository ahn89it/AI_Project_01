"""임베딩 서비스 추상화.

1차 방침(CLAUDE.md): Ollama에 multilingual-e5-large를 등록해 사용.
확인 결과 Ollama 공식 라이브러리에는 정확히 이 이름의 모델이 없다(가장 가까운 대안도
BGE 계열이라 CLAUDE.md의 "중국 모델(Qwen/BGE 계열) 사용 금지" 규정에 걸림). 따라서
2차 방침인 sentence-transformers 직접 로딩(CPU)을 사용한다 — D1에서 이미 정상 동작을
검증했다. 이후 Ollama가 해당 모델을 지원하게 되더라도 이 모듈만 교체하면 되도록
EmbeddingService 인터페이스로 감싸 둔다 (analyzer/indexer.py, server/services/retriever.py는
구현 방식을 몰라도 된다).

e5 계열 규약: 문서 임베딩은 "passage: " 접두사, 질의 임베딩은 "query: " 접두사가
반드시 붙어야 한다 (누락 시 검색 품질이 크게 떨어짐).
"""
from __future__ import annotations

import logging
from functools import lru_cache
from typing import List

from server.config import EMBEDDING_MODEL

logger = logging.getLogger(__name__)


class EmbeddingService:
    """임베딩 백엔드 공통 인터페이스."""

    def embed_documents(self, texts: List[str], batch_size: int = 16) -> List[List[float]]:
        raise NotImplementedError

    def embed_query(self, text: str) -> List[float]:
        raise NotImplementedError


class SentenceTransformerEmbedding(EmbeddingService):
    """sentence-transformers 기반 구현 (CPU 고정 — GPU는 EXAONE 전용)."""

    def __init__(self, model_name: str = EMBEDDING_MODEL):
        from sentence_transformers import SentenceTransformer

        logger.info("임베딩 모델 로딩 중: %s (CPU)", model_name)
        self._model = SentenceTransformer(model_name, device="cpu")

    def embed_documents(self, texts: List[str], batch_size: int = 16) -> List[List[float]]:
        prefixed = [f"passage: {t}" for t in texts]
        embeddings = self._model.encode(
            prefixed, batch_size=batch_size, show_progress_bar=False, normalize_embeddings=True,
        )
        return embeddings.tolist()

    def embed_query(self, text: str) -> List[float]:
        embeddings = self._model.encode([f"query: {text}"], normalize_embeddings=True)
        return embeddings[0].tolist()


@lru_cache(maxsize=1)
def get_embedding_service() -> EmbeddingService:
    """프로세스당 모델을 한 번만 로딩(수십 초 소요)해 재사용한다."""
    return SentenceTransformerEmbedding()
