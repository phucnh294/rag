"""Cross-encoder rerank of the top-k retrieved chunks.

Scores each (question, chunk) pair via the rerank-service (a local
cross-encoder, see config/llm_setup.py:rerank_scores_martin), then returns
the top_n chunks ordered by that score instead of the original vector
similarity.
"""

from __future__ import annotations

from config.env_config import RagConfig
from config.llm_setup import rerank_scores_martin
from retrieval.step4_similarity_search import RetrievedChunk


def rerank_chunks_martin(
    config: RagConfig, question: str, chunks: list[RetrievedChunk], top_n: int = 5
) -> list[RetrievedChunk]:
    """Return the top_n chunks reordered by cross-encoder relevance to question."""
    if not chunks:
        return []

    scores = rerank_scores_martin(config, question, [chunk["content"] for chunk in chunks])
    rescored = [
        RetrievedChunk(
            chunk_id=chunk["chunk_id"],
            content=chunk["content"],
            source_path=chunk["source_path"],
            status=chunk["status"],
            area=chunk["area"],
            found_by=chunk["found_by"],
            score=score,
        )
        for chunk, score in zip(chunks, scores)
    ]
    rescored.sort(key=lambda chunk: chunk["score"], reverse=True)
    return rescored[:top_n]
