"""Structure-aware chunking of the document body.

Task (see rag-structure.md > indexing/): ~800 tokens per chunk, paragraph
overlap between chunks. Splits along markdown structure (headings,
paragraphs) first so a chunk boundary never falls mid-sentence or
separates a heading from the text it introduces; only falls back to a
raw token-sliding-window for a single block too large to fit one chunk
(e.g. a huge table or code block).
"""

from __future__ import annotations

import re

import tiktoken

CHUNK_SIZE_TOKENS = 800
CHUNK_OVERLAP_TOKENS = 120  # used only by the oversized-block fallback below
_CHUNK_OVERLAP_PARAGRAPHS = 1  # paragraphs carried forward into the next chunk

_ENCODING = tiktoken.get_encoding("cl100k_base")
_BLANK_LINE_RE = re.compile(r"\n\s*\n")
_HEADING_RE = re.compile(r"^#{1,6}\s+\S")


def _token_count_martin(text: str) -> int:
    """Return the tiktoken token count of text."""
    return len(_ENCODING.encode(text))


def _starts_with_heading_martin(text: str) -> bool:
    """Return True if text's first line is a markdown heading."""
    return bool(_HEADING_RE.match(text.lstrip("\n")))


def _split_into_blocks_martin(body_text: str) -> list[str]:
    """Split body_text into blank-line-separated blocks.

    A bare heading block (nothing else on its own paragraph) is merged into
    the block that follows it, so a heading is never separated from the
    text it introduces when blocks are later packed into chunks.
    """
    raw_blocks = [b.strip() for b in _BLANK_LINE_RE.split(body_text.strip()) if b.strip()]
    merged: list[str] = []
    for block in raw_blocks:
        if merged and "\n" not in merged[-1] and _starts_with_heading_martin(merged[-1]):
            merged[-1] = f"{merged[-1]}\n\n{block}"
        else:
            merged.append(block)
    return merged


def _split_oversized_block_martin(block: str) -> list[str]:
    """Fall back to fixed-token sliding-window splitting for one oversized block."""
    tokens = _ENCODING.encode(block)
    step = CHUNK_SIZE_TOKENS - CHUNK_OVERLAP_TOKENS
    pieces: list[str] = []
    start = 0
    while start < len(tokens):
        end = min(start + CHUNK_SIZE_TOKENS, len(tokens))
        pieces.append(_ENCODING.decode(tokens[start:end]))
        if end == len(tokens):
            break
        start += step
    return pieces


def chunk_body_martin(body_text: str) -> list[str]:
    """Split body_text into structure-aware chunks with paragraph overlap.

    Blocks (headings + the paragraph they introduce, or standalone
    paragraphs) are packed greedily up to CHUNK_SIZE_TOKENS. The last
    `_CHUNK_OVERLAP_PARAGRAPHS` block(s) of a chunk carry forward into the
    next one so context still bridges a chunk boundary. A chunk that
    doesn't start under its own heading is prefixed with the most recent
    heading seen, so every chunk carries the section title it belongs to.
    """
    blocks = _split_into_blocks_martin(body_text)
    if not blocks:
        return []

    chunks: list[str] = []
    current: list[str] = []
    current_tokens = 0
    current_heading: str | None = None
    chunk_heading: str | None = None

    def _flush_martin() -> None:
        if not current:
            return
        text = "\n\n".join(current)
        if chunk_heading is not None and not _starts_with_heading_martin(current[0]):
            text = f"{chunk_heading}\n\n{text}"
        chunks.append(text)

    for block in blocks:
        if _starts_with_heading_martin(block):
            current_heading = block.splitlines()[0]

        block_tokens = _token_count_martin(block)

        if block_tokens > CHUNK_SIZE_TOKENS:
            _flush_martin()
            current, current_tokens, chunk_heading = [], 0, None
            chunks.extend(_split_oversized_block_martin(block))
            continue

        if current and current_tokens + block_tokens > CHUNK_SIZE_TOKENS:
            _flush_martin()
            current = current[-_CHUNK_OVERLAP_PARAGRAPHS:]
            current_tokens = sum(_token_count_martin(b) for b in current)
            chunk_heading = current_heading

        if not current:
            chunk_heading = current_heading
        current.append(block)
        current_tokens += block_tokens

    _flush_martin()
    return chunks
