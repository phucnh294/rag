"""Fixed-token chunking of the document body.

Task (see rag-structure.md > indexing/): 800 tokens per chunk, 120 token
overlap. Return the chunks in order.
"""

from __future__ import annotations

import tiktoken

CHUNK_SIZE_TOKENS = 800
CHUNK_OVERLAP_TOKENS = 120

_ENCODING = tiktoken.get_encoding("cl100k_base")


def chunk_body_martin(body_text: str) -> list[str]:
    """Split body_text into fixed-token chunks with overlap."""
    tokens = _ENCODING.encode(body_text)
    if not tokens:
        return []

    step = CHUNK_SIZE_TOKENS - CHUNK_OVERLAP_TOKENS
    chunks: list[str] = []
    start = 0
    while start < len(tokens):
        end = min(start + CHUNK_SIZE_TOKENS, len(tokens))
        chunks.append(_ENCODING.decode(tokens[start:end]))
        if end == len(tokens):
            break
        start += step
    return chunks
