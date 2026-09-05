"""Parse frontmatter into title/date/area/status/tags/summary.

Task (see rag-structure.md > indexing/): parse the YAML frontmatter block
(if present) into a metadata dict. Returns {} when there's no frontmatter
or it fails to parse.
"""

from __future__ import annotations

from typing import Any

import yaml


def extract_metadata_martin(frontmatter_block: str) -> dict[str, Any]:
    """Return the parsed frontmatter as a dict, or {} if absent/invalid."""
    if not frontmatter_block.strip():
        return {}
    try:
        parsed = yaml.safe_load(frontmatter_block)
    except yaml.YAMLError:
        return {}
    return parsed if isinstance(parsed, dict) else {}
