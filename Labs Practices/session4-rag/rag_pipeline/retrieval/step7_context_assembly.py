"""Concatenate retrieved chunk texts into a single context block.

Task (see rag-structure.md > retrieval/): join the (reranked) chunks'
content into one context string for the prompt.
"""

from __future__ import annotations

from typing import Any


def assemble_context_martin(chunks: list[Any]) -> str:
    """Return one context string built from the given chunks."""
    return "\n\n---\n\n".join(chunk["content"] for chunk in chunks)
