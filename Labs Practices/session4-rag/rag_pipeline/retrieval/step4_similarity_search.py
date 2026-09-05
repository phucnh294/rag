"""Cosine top-k search against rag_embeddings.

Task (see rag-structure.md > retrieval/): ORDER BY embedding <=> %s LIMIT
k, joined back to rag_chunks/rag_documents for content + source_path.
"""

from __future__ import annotations

from typing import Any, TypedDict

from shared.pgvector_utils import to_vector_literal_martin


class RetrievedChunk(TypedDict):
    """One retrieved chunk with enough context to build the prompt/answer."""

    content: str
    source_path: str
    score: float
    status: str | None
    area: str | None


def similarity_search_martin(
    conn: Any, question_embedding: list[float], top_k: int = 5
) -> list[RetrievedChunk]:
    """Return the top_k most similar chunks to the question embedding."""
    vector_literal = to_vector_literal_martin(question_embedding)
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT c.content, d.source_path, d.status, d.area,
                   (e.embedding <=> %s::vector) AS distance
            FROM rag_embeddings e
            JOIN rag_chunks c ON c.id = e.chunk_id
            JOIN rag_documents d ON d.id = c.document_id
            ORDER BY e.embedding <=> %s::vector
            LIMIT %s
            """,
            (vector_literal, vector_literal, top_k),
        )
        rows = cur.fetchall()

    return [
        RetrievedChunk(
            content=content, source_path=source_path, status=status, area=area, score=1.0 - distance
        )
        for content, source_path, status, area, distance in rows
    ]
