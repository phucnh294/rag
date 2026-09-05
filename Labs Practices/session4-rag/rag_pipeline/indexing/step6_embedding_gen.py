"""Embed each cleaned chunk via nomic-embed-text.

Task (see rag-structure.md > indexing/): call config/llm_setup.py's
embed_text_martin on each chunk. Return one 768-dim vector per chunk.
"""

from __future__ import annotations

from config.env_config import RagConfig
from config.llm_setup import embed_text_martin


def generate_embeddings_martin(config: RagConfig, chunks: list[str]) -> list[list[float]]:
    """Return one embedding vector per chunk, same order as chunks."""
    return [embed_text_martin(config, chunk) for chunk in chunks]
