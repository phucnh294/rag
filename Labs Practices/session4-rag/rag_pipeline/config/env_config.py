"""Load and validate pipeline configuration from environment variables.

Task (see rag-structure.md > config/): read all vars from .env.rag (DB
creds, OLLAMA_NOMIC_EMBED_TEXT_HOST/_PORT, RERANK_HOST/_PORT (+ the
RERANK_ENABLED default), CHAT_PROVIDER + that provider's own vars,
EMBEDDING_DIM) into one typed config object. Fail fast on a missing
required var.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class RagConfig:
    """Typed bundle of everything indexing/retrieval need at runtime."""

    postgres_host: str
    postgres_port: int
    postgres_user: str
    postgres_password: str
    postgres_db: str
    embedding_dim: int
    nomic_host: str
    nomic_port: int
    nomic_model: str
    rerank_enabled: bool
    rerank_host: str
    rerank_port: int
    hybrid_enabled: bool
    chat_provider: str
    llama_host: str
    llama_port: int
    llama_model: str
    gemini_api_key: str
    gemini_model: str


def load_config_martin() -> RagConfig:
    """Read and validate all required env vars into a RagConfig.

    Only the vars required by the selected CHAT_PROVIDER are enforced —
    e.g. GEMINI_API_KEY is not required when CHAT_PROVIDER=ollama, and
    vice versa. See config/llm_setup.py's _CHAT_BACKENDS for the set of
    supported provider names. RERANK_HOST/RERANK_HOST_PORT are always
    required (regardless of RERANK_ENABLED's default), since a per-request
    override — e.g. {"rerank": true} on POST /chat — can force reranking
    on even when the server-wide default is off, and vice versa.

    Raises:
        KeyError: a required env var (for the active provider) is missing.
    """
    try:
        chat_provider = os.environ.get("CHAT_PROVIDER", "ollama").strip().lower()
        rerank_enabled = os.environ.get("RERANK_ENABLED", "true").strip().lower() in (
            "1",
            "true",
            "yes",
            "on",
        )
        hybrid_enabled = os.environ.get("HYBRID_SEARCH_ENABLED", "false").strip().lower() in (
            "1",
            "true",
            "yes",
            "on",
        )

        llama_host, llama_port, llama_model = "", 0, ""
        gemini_api_key, gemini_model = "", ""

        rerank_host = os.environ["RERANK_HOST"]
        rerank_port = int(os.environ["RERANK_HOST_PORT"])

        if chat_provider == "ollama":
            llama_host = os.environ["OLLAMA_LLAMA31_HOST"]
            llama_port = int(os.environ["OLLAMA_LLAMA31_HOST_PORT"])
            llama_model = os.environ["OLLAMA_LLAMA31_MODEL"]
        elif chat_provider == "gemini":
            gemini_api_key = os.environ["GEMINI_API_KEY"]
            gemini_model = os.environ["GEMINI_MODEL"]
        else:
            raise KeyError(f"CHAT_PROVIDER={chat_provider!r} (unknown provider)")

        return RagConfig(
            postgres_host=os.environ["POSTGRES_HOST"],
            postgres_port=int(os.environ["POSTGRES_HOST_PORT"]),
            postgres_user=os.environ["POSTGRES_USER"],
            postgres_password=os.environ["POSTGRES_PASSWORD"],
            postgres_db=os.environ["POSTGRES_DB"],
            embedding_dim=int(os.environ["EMBEDDING_DIM"]),
            nomic_host=os.environ["OLLAMA_NOMIC_EMBED_TEXT_HOST"],
            nomic_port=int(os.environ["OLLAMA_NOMIC_EMBED_TEXT_HOST_PORT"]),
            nomic_model=os.environ["OLLAMA_NOMIC_EMBED_TEXT_MODEL"],
            rerank_enabled=rerank_enabled,
            rerank_host=rerank_host,
            rerank_port=rerank_port,
            hybrid_enabled=hybrid_enabled,
            chat_provider=chat_provider,
            llama_host=llama_host,
            llama_port=llama_port,
            llama_model=llama_model,
            gemini_api_key=gemini_api_key,
            gemini_model=gemini_model,
        )
    except KeyError as err:
        raise KeyError(f"Missing required env var: {err}") from err
