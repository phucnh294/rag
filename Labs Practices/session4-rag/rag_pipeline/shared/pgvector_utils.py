"""Helpers for talking to Postgres' pgvector columns via psycopg2.

psycopg2 has no built-in adapter for the `vector` type, so embeddings are
passed as a bracketed text literal and cast in SQL with `%s::vector`.
"""

from __future__ import annotations


def to_vector_literal_martin(embedding: list[float]) -> str:
    """Format a Python float list as a pgvector input literal, e.g. "[0.1,0.2]"."""
    return "[" + ",".join(repr(float(value)) for value in embedding) + "]"
