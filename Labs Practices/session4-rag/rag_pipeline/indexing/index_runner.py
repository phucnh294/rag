"""Orchestrate the indexing process (steps 1-8) for one uploaded file.

Task (see rag-structure.md > indexing/): wire step1..step8 together and
return chunks_indexed for the API response.
"""

from __future__ import annotations

from pathlib import Path

from config.db_connection import get_connection_martin
from config.env_config import RagConfig
from indexing.step1_load_input import load_input_martin
from indexing.step2_document_parsing import parse_document_martin
from indexing.step3_chunking_strategy import chunk_body_martin
from indexing.step4_preprocessing import preprocess_chunks_martin
from indexing.step5_metadata_extraction import extract_metadata_martin
from indexing.step6_embedding_gen import generate_embeddings_martin
from indexing.step7_store_documents import store_document_martin
from indexing.step8_store_chunks import store_chunks_martin


def run_indexing_martin(
    config: RagConfig, file_path: Path, status: str | None = None, area: str | None = None
) -> int:
    """Index one .md file end-to-end. Return the number of chunks indexed.

    `status`/`area` override whatever the file's own frontmatter says —
    this lets an upload explicitly tag a document without needing
    frontmatter in the file itself.
    """
    source_path, raw_text = load_input_martin(file_path)
    frontmatter_block, body_text = parse_document_martin(raw_text)
    frontmatter_metadata = extract_metadata_martin(frontmatter_block)
    resolved_status = status or frontmatter_metadata.get("status")
    resolved_area = area or frontmatter_metadata.get("area")
    # title/doc_date/tags/doc_type have no upload-form override (unlike
    # status/area) — they only ever come from frontmatter, since this
    # project's frontmatter schema (rag-ai-local/template/) already
    # defines them and there's no per-upload UI need for them yet.
    title = frontmatter_metadata.get("title")
    doc_date = frontmatter_metadata.get("date")
    tags = frontmatter_metadata.get("tags")
    doc_type = frontmatter_metadata.get("type")  # frontmatter key is "type", column is doc_type

    raw_chunks = chunk_body_martin(body_text)
    chunks = preprocess_chunks_martin(raw_chunks)
    embeddings = generate_embeddings_martin(config, chunks)

    conn = get_connection_martin(config)
    try:
        document_id = store_document_martin(
            conn,
            source_path,
            raw_text,
            status=resolved_status,
            area=resolved_area,
            title=title,
            doc_date=doc_date,
            tags=tags,
            doc_type=doc_type,
        )
        return store_chunks_martin(conn, document_id, chunks, embeddings, config.nomic_model)
    finally:
        conn.close()
