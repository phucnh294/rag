"""Parse/strip a YAML frontmatter block from a markdown string.

Task (see rag-structure.md > shared/): used by indexing/step2. Split a
raw markdown string on the leading `---`...`---` delimiters.
"""

from __future__ import annotations

import re

_FRONTMATTER_RE = re.compile(r"\A---\n(.*?\n)?---[ \t]*\n?", re.DOTALL)


def split_frontmatter_martin(raw_text: str) -> tuple[str, str]:
    """Return (frontmatter_block, body_text). frontmatter_block is "" if absent."""
    match = _FRONTMATTER_RE.match(raw_text)
    if not match:
        return "", raw_text
    frontmatter_block = (match.group(1) or "").rstrip("\n")
    body_text = raw_text[match.end() :]
    return frontmatter_block, body_text
