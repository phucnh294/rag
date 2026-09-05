"""Full-text (sparse) search against rag_chunks.content_tsv.

Complements step4_similarity_search.py's dense/vector search — same
candidate-list shape (RetrievedChunk), fused with the vector ranking via
fusion.py's Reciprocal Rank Fusion.
"""

from __future__ import annotations

from typing import Any

from retrieval.step4_similarity_search import RetrievedChunk


def lexical_search_martin(conn: Any, query_text: str, top_k: int) -> list[RetrievedChunk]:
    """Return the top_k chunks whose content_tsv matches query_text, by ts_rank."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT c.id, c.content, d.source_path, d.status, d.area,
                   ts_rank(c.content_tsv, websearch_to_tsquery('english', %s)) AS score
            FROM rag_chunks c
            JOIN rag_documents d ON d.id = c.document_id
            WHERE c.content_tsv @@ websearch_to_tsquery('english', %s)
            ORDER BY score DESC
            LIMIT %s
            """,
            (query_text, query_text, top_k),
        )
        rows = cur.fetchall()

    return [
        RetrievedChunk(
            chunk_id=str(chunk_id),
            content=content,
            source_path=source_path,
            status=status,
            area=area,
            score=score,
            found_by="lexical",
        )
        for chunk_id, content, source_path, status, area, score in rows
    ]
