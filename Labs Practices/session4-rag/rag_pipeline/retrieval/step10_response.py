"""Shape the final API response.

Task (see rag-structure.md > retrieval/): {"answer": str, "sources":
list[str]} — sources = de-duplicated source_path/filenames of the chunks
actually used.
"""

from __future__ import annotations

from typing import Any


def _format_scored_chunks_martin(chunks: list[Any]) -> list[dict[str, Any]]:
    """Return [{"source_path", "score", "content", "status", "area"}, ...] for debugging."""
    return [
        {
            "source_path": chunk["source_path"],
            "score": round(chunk["score"], 4),
            "content": chunk["content"],
            "status": chunk.get("status"),
            "area": chunk.get("area"),
        }
        for chunk in chunks
    ]


def build_response_martin(
    answer: str,
    chunks: list[Any],
    rerank_applied: bool,
    before_rerank: list[Any],
    excluded_count: int = 0,
    restricted_to_current: bool = False,
) -> dict[str, Any]:
    """Return the {"answer", "sources", "reranked", "retrieval_scores"} dict.

    "reranked" and "retrieval_scores" are additive to the lab's
    {"answer", "sources"} contract. "reranked" reports whether this specific
    request actually ran the cross-encoder reranker; "retrieval_scores"
    carries every candidate considered (not just the final top_n) from
    before and (if it ran) after reranking — including chunk content and
    status — so callers (e.g. a debug panel) can inspect exactly what the
    reranker saw and how it moved things, not just infer it from `sources`.

    before_rerank is the FULL candidate pool passed into reranking (up to
    the runner's candidate-pool size, already post-metadata-filter), while
    `chunks`/after_rerank is whatever was actually used for the answer
    (already truncated to top_n). `excluded_count`/`restricted_to_current`
    report what step5_metadata_filter.py did before any of this ran.
    """
    sources = list(dict.fromkeys(chunk["source_path"] for chunk in chunks))
    return {
        "answer": answer,
        "sources": sources,
        "reranked": rerank_applied,
        "retrieval_scores": {
            "before_rerank": _format_scored_chunks_martin(before_rerank),
            "after_rerank": _format_scored_chunks_martin(chunks) if rerank_applied else None,
            "metadata_filter": {
                "excluded_count": excluded_count,
                "restricted_to_current": restricted_to_current,
            },
        },
    }
