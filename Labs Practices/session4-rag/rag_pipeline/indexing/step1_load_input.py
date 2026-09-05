"""Read one .md file's raw text.

Task (see rag-structure.md > indexing/): given a file path (the file
/upload just saved into input/), return (source_path, raw_text).
"""

from __future__ import annotations

from pathlib import Path


def load_input_martin(file_path: Path) -> tuple[str, str]:
    """Return (source_path, raw_text) for the given markdown file."""
    raw_text = file_path.read_text(encoding="utf-8")
    return str(file_path), raw_text
