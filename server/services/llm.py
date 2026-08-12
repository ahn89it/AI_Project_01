"""Ollama(EXAONE) 클라이언트. 모든 LLM 호출은 이 모듈 하나로 통일한다.

CLAUDE.md 원칙: 외부 LLM API 절대 금지, localhost Ollama만 경유.
"""
from __future__ import annotations

import logging

import httpx

from server.config import LLM_MODEL, OLLAMA_HOST

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 120.0


class OllamaConnectionError(RuntimeError):
    """Ollama 서버에 연결할 수 없을 때 발생 (호출부가 사용자에게 그대로 보여줄 수 있는 메시지 포함)."""


def chat(system: str, user: str, temperature: float = 0.2, timeout: float = DEFAULT_TIMEOUT) -> str:
    """Ollama /api/chat 호출. 사실 기반 답변이 목적이므로 temperature 기본값은 낮게(0.2) 둔다."""
    url = f"{OLLAMA_HOST}/api/chat"
    payload = {
        "model": LLM_MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "stream": False,
        "options": {"temperature": temperature},
    }

    try:
        response = httpx.post(url, json=payload, timeout=timeout)
        response.raise_for_status()
    except httpx.ConnectError as e:
        raise OllamaConnectionError(
            "Ollama에 연결할 수 없습니다. Ollama가 실행 중인지 확인하세요: ollama serve"
        ) from e
    except httpx.TimeoutException as e:
        raise OllamaConnectionError(
            f"Ollama 응답이 {timeout:.0f}초 내에 오지 않았습니다. 모델이 아직 로딩 중이거나 컨텍스트가 너무 길 수 있습니다."
        ) from e
    except httpx.HTTPStatusError as e:
        logger.error("Ollama 응답 오류: %s", e.response.text)
        raise OllamaConnectionError(f"Ollama가 오류를 반환했습니다: {e.response.status_code}") from e

    data = response.json()
    return data["message"]["content"]
