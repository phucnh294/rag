"""Upsert one row into rag_documents.

Task (see rag-structure.md > indexing/): ON CONFLICT (source_path) DO
UPDATE with (source_path, raw_content, status, area). Return the document_id.
"""

from __future__ import annotations

from typing import Any


def store_document_martin(
    conn: Any,
    source_path: str,
    raw_content: str,
    status: str | None = None,
    area: str | None = None,
) -> str:
    """Upsert the document row and return its document_id."""
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO rag_documents (source_path, raw_content, status, area)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (source_path) DO UPDATE
                SET raw_content = EXCLUDED.raw_content,
                    status = EXCLUDED.status,
                    area = EXCLUDED.area
            RETURNING id
            """,
            (source_path, raw_content, status, area),
        )
        document_id = cur.fetchone()[0]
    conn.commit()
    return str(document_id)
