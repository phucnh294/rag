"""Reciprocal Rank Fusion (RRF) — merge multiple rankings into one.

Standard IR technique: a chunk's fused score is the sum, across every
ranking it appears in, of 1/(k + rank). A chunk present in more than one
ranking naturally outscores one found by only a single method, without
needing the two methods' raw scores (cosine distance vs. ts_rank) to be
on comparable scales.
"""

from __future__ import annotations

from retrieval.step4_similarity_search import RetrievedChunk

_DEFAULT_RRF_K = 60


def reciprocal_rank_fusion_martin(
    rankings: list[list[RetrievedChunk]], k: int = _DEFAULT_RRF_K, top_k: int = 20
) -> list[RetrievedChunk]:
    """Fuse rankings (each already ordered best-first) into one, keyed by chunk_id."""
    scores: dict[str, float] = {}
    found_by: dict[str, set[str]] = {}
    chunk_by_id: dict[str, RetrievedChunk] = {}

    for ranking in rankings:
        for rank, chunk in enumerate(ranking, start=1):
            chunk_id = chunk["chunk_id"]
            scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (k + rank)
            found_by.setdefault(chunk_id, set()).add(chunk["found_by"])
            chunk_by_id.setdefault(chunk_id, chunk)

    fused = [
        {
            **chunk_by_id[chunk_id],
            "score": scores[chunk_id],
            "found_by": _resolve_found_by_martin(found_by[chunk_id]),
        }
        for chunk_id in chunk_by_id
    ]
    fused.sort(key=lambda chunk: chunk["score"], reverse=True)
    return fused[:top_k]


def _resolve_found_by_martin(sources: set[str]) -> str:
    """Return "both" if more than one method surfaced this chunk, else the single method."""
    return "both" if len(sources) > 1 else next(iter(sources))
