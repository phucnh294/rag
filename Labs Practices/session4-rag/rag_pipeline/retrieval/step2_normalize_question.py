"""Normalize the question text before embedding.

Task (see rag-structure.md > retrieval/): whitespace/casing cleanup as
needed before it's sent to the embedding model.
"""

from __future__ import annotations

import re

_WHITESPACE_RE = re.compile(r"\s+")


def normalize_question_martin(question: str) -> str:
    """Return a normalized copy of the question."""
    return _WHITESPACE_RE.sub(" ", question.strip())
