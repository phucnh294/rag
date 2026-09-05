"""Clean each chunk before embedding.

Task (see rag-structure.md > indexing/): strip control chars, collapse
excess whitespace.
"""

from __future__ import annotations

import re

_CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_INLINE_WHITESPACE_RE = re.compile(r"[ \t]+")
_EXCESS_BLANK_LINES_RE = re.compile(r"\n{3,}")


def preprocess_chunks_martin(chunks: list[str]) -> list[str]:
    """Return cleaned copies of the given chunks."""
    cleaned: list[str] = []
    for chunk in chunks:
        text = _CONTROL_CHARS_RE.sub("", chunk)
        text = _INLINE_WHITESPACE_RE.sub(" ", text)
        text = _EXCESS_BLANK_LINES_RE.sub("\n\n", text)
        cleaned.append(text.strip())
    return cleaned
