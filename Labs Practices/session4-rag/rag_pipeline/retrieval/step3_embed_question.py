"""Embed the normalized question via nomic-embed-text.

Task (see rag-structure.md > retrieval/): call config/llm_setup.py's
embed_text_martin on the question. Return the question vector.
"""

from __future__ import annotations

from config.env_config import RagConfig
from config.llm_setup import embed_text_martin


def embed_question_martin(config: RagConfig, question: str) -> list[float]:
    """Return the embedding vector for the question."""
    return embed_text_martin(config, question)
