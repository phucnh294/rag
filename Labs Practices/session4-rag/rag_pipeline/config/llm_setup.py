"""Clients for calling the embedding model, the reranker, and the chat model.

One function per model call — embed(text) -> list[float] via Ollama's
nomic-embed-text, rerank(query, documents) -> list[float] via the local
cross-encoder rerank-service, chat(prompt) -> str via whichever backend
config.chat_provider selects (see _CHAT_BACKENDS below).
"""

from __future__ import annotations

import time
from typing import Callable

import requests

from config.env_config import RagConfig

_RETRYABLE_STATUS_CODES = {429, 503}
_MAX_ATTEMPTS = 3
_RETRY_BACKOFF_SECONDS = 2


def embed_text_martin(config: RagConfig, text: str) -> list[float]:
    """Return the embedding vector for one piece of text via nomic-embed-text."""
    url = f"http://{config.nomic_host}:{config.nomic_port}/api/embeddings"
    response = requests.post(
        url, json={"model": config.nomic_model, "prompt": text}, timeout=60
    )
    response.raise_for_status()
    return response.json()["embedding"]


def rerank_scores_martin(config: RagConfig, query: str, documents: list[str]) -> list[float]:
    """Return one relevance score per document (same order) via the rerank-service."""
    if not documents:
        return []
    url = f"http://{config.rerank_host}:{config.rerank_port}/rerank"
    response = requests.post(
        url, json={"query": query, "documents": documents}, timeout=30
    )
    response.raise_for_status()
    return response.json()["scores"]


def _chat_ollama_martin(config: RagConfig, prompt: str) -> tuple[str, dict]:
    """Call a local Ollama model's /api/generate. Return (answer, request_payload_sent)."""
    url = f"http://{config.llama_host}:{config.llama_port}/api/generate"
    payload = {"model": config.llama_model, "prompt": prompt, "stream": False}
    response = requests.post(url, json=payload, timeout=600)
    response.raise_for_status()
    return response.json()["response"], payload


def _chat_gemini_martin(config: RagConfig, prompt: str) -> tuple[str, dict]:
    """Call Google AI Studio's Gemini API, retrying on transient errors/timeouts.

    Returns (answer, request_payload_sent). The API key travels as a URL
    query param, not in the JSON body, so the returned payload never
    contains it.
    """
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{config.gemini_model}:generateContent"
    )
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    last_timeout: requests.exceptions.Timeout | None = None
    for attempt in range(_MAX_ATTEMPTS):
        is_last_attempt = attempt == _MAX_ATTEMPTS - 1

        try:
            response = requests.post(
                url, params={"key": config.gemini_api_key}, json=payload, timeout=60
            )
        except requests.exceptions.Timeout as err:
            last_timeout = err
            if is_last_attempt:
                raise
            time.sleep(_RETRY_BACKOFF_SECONDS * (attempt + 1))
            continue

        if response.status_code in _RETRYABLE_STATUS_CODES and not is_last_attempt:
            time.sleep(_RETRY_BACKOFF_SECONDS * (attempt + 1))
            continue

        response.raise_for_status()
        data = response.json()
        return data["candidates"][0]["content"]["parts"][0]["text"], payload

    assert last_timeout is not None  # loop always returns/raises above otherwise
    raise last_timeout


# Add a new provider by writing a _chat_<name>_martin(config, prompt) -> (str, dict)
# function above and registering it here under CHAT_PROVIDER's value.
_CHAT_BACKENDS: dict[str, Callable[[RagConfig, str], tuple[str, dict]]] = {
    "ollama": _chat_ollama_martin,
    "gemini": _chat_gemini_martin,
}


def chat_martin(config: RagConfig, prompt: str) -> tuple[str, dict]:
    """Return (answer, request_payload_sent) for the configured chat model.

    Dispatches to the backend named by config.chat_provider (CHAT_PROVIDER
    env var) — currently "ollama" or "gemini". request_payload_sent is the
    exact JSON body posted to the provider's API (never includes secrets —
    the Gemini API key travels as a URL param, not in this body), returned
    so callers can audit-log precisely what was sent.
    """
    try:
        backend = _CHAT_BACKENDS[config.chat_provider]
    except KeyError as err:
        raise ValueError(f"Unknown CHAT_PROVIDER: {config.chat_provider!r}") from err
    return backend(config, prompt)
