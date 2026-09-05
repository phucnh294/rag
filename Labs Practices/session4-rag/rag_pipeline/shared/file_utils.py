"""Filesystem helpers for reading/writing under input/.

Task (see rag-structure.md > shared/): list .md files under input/, and
safely write an uploaded file into input/ (sanitize the filename).
"""

from __future__ import annotations

import re
from pathlib import Path

_UNSAFE_CHARS_RE = re.compile(r"[^A-Za-z0-9._-]+")


def list_input_files_martin(input_dir: Path) -> list[Path]:
    """Return all .md file paths under input_dir."""
    if not input_dir.exists():
        return []
    return sorted(input_dir.glob("*.md"))


def save_upload_martin(input_dir: Path, filename: str, content: bytes) -> Path:
    """Write an uploaded file's bytes into input_dir with a sanitized filename."""
    input_dir.mkdir(parents=True, exist_ok=True)

    safe_name = _UNSAFE_CHARS_RE.sub("_", Path(filename).name) or "upload.md"
    if not safe_name.lower().endswith(".md"):
        safe_name += ".md"

    dest_path = input_dir / safe_name
    dest_path.write_bytes(content)
    return dest_path
