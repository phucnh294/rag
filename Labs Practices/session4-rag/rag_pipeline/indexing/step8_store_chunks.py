"""Store each chunk + its embedding.

Task (see rag-structure.md > indexing/): for each (chunk_text, embedding)
pair, insert into rag_chunks (document_id, chunk_index, content,
token_count), then insert the matching rag_embeddings row (chunk_id,
embedding, model).
"""

from __future__ import annotations

from typing import Any

import tiktoken

from shared.pgvector_utils import to_vector_literal_martin

_ENCODING = tiktoken.get_encoding("cl100k_base")


def store_chunks_martin(
    conn: Any,
    document_id: str,
    chunks: list[str],
    embeddings: list[list[float]],
    model_name: str,
) -> int:
    """Persist all chunks + embeddings for one document. Return chunks stored."""
    stored = 0
    with conn.cursor() as cur:
        for chunk_index, (chunk_text, embedding) in enumerate(zip(chunks, embeddings)):
            token_count = len(_ENCODING.encode(chunk_text))
            cur.execute(
                """
                INSERT INTO rag_chunks (document_id, chunk_index, content, token_count)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (document_id, chunk_index) DO UPDATE
                    SET content = EXCLUDED.content, token_count = EXCLUDED.token_count
                RETURNING id
                """,
                (document_id, chunk_index, chunk_text, token_count),
            )
            chunk_id = cur.fetchone()[0]

            cur.execute(
                """
                INSERT INTO rag_embeddings (chunk_id, embedding, model)
                VALUES (%s, %s::vector, %s)
                ON CONFLICT (chunk_id) DO UPDATE
                    SET embedding = EXCLUDED.embedding, model = EXCLUDED.model
                """,
                (chunk_id, to_vector_literal_martin(embedding), model_name),
            )
            stored += 1
    conn.commit()
    return stored
