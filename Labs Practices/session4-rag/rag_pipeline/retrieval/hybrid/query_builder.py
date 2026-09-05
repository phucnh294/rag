"""Turn a question into text suitable for Postgres full-text search.

Task: no manual tsquery-syntax construction here — Postgres'
`websearch_to_tsquery('english', %s)` already parses natural-language
phrasing (including quotes/AND/OR/exclusions) safely as a bind parameter.
This module only does the light normalization worth doing before that.
"""

from __future__ import annotations

import re

_WHITESPACE_RE = re.compile(r"\s+")


def build_tsquery_text_martin(question: str) -> str:
    """Return question, trimmed and whitespace-collapsed, for websearch_to_tsquery."""
    return _WHITESPACE_RE.sub(" ", question).strip()
