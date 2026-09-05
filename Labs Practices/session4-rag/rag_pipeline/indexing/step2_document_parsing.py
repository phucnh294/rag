"""Split raw markdown into (frontmatter_block, body_text).

Task (see rag-structure.md > indexing/): find the `---`...`---` delimiters
and split on them. Lab1 only needs the split, not field-by-field parsing
(that's step5_metadata_extraction, Lab2).
"""

from __future__ import annotations

from shared.md_frontmatter import split_frontmatter_martin


def parse_document_martin(raw_text: str) -> tuple[str, str]:
    """Return (frontmatter_block, body_text) split from raw_text."""
    return split_frontmatter_martin(raw_text)
