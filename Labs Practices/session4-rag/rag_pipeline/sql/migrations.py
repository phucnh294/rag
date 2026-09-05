"""Idempotent, hash-tracked schema migrations for the RAG pipeline.

Applies init_rag_db.sql on startup. The schema file is idempotent
(CREATE TABLE IF NOT EXISTS), so this module only re-executes it when the
file's content hash differs from the last applied hash, avoiding a needless
round-trip to Postgres on every ordinary restart.
"""

from __future__ import annotations

import hashlib
import logging
import os
from pathlib import Path

import psycopg2
from psycopg2.extensions import connection as PgConnection

logger = logging.getLogger(__name__)

_SQL_FILE_PATH = Path(__file__).parent / "init_rag_db.sql"
_MIGRATIONS_TABLE = "schema_migrations"
_DEFAULT_EMBEDDING_DIM = "768"


class MigrationError(Exception):
    """Raised when the schema migration cannot be prepared or applied."""


def _get_db_connection_martin() -> PgConnection:
    """Open a Postgres connection using env-configured credentials.

    Raises:
        MigrationError: a required POSTGRES_* env var is missing.
    """
    try:
        return psycopg2.connect(
            host=os.environ["POSTGRES_HOST"],
            port=os.environ["POSTGRES_HOST_PORT"],
            user=os.environ["POSTGRES_USER"],
            password=os.environ["POSTGRES_PASSWORD"],
            dbname=os.environ["POSTGRES_DB"],
        )
    except KeyError as err:
        raise MigrationError(f"Missing required env var: {err}") from err


def _load_sql_martin() -> str:
    """Read init_rag_db.sql and substitute {{EMBEDDING_DIM}} with the real value.

    Raises:
        MigrationError: the schema file does not exist next to this module.
    """
    if not _SQL_FILE_PATH.exists():
        raise MigrationError(f"Schema file not found: {_SQL_FILE_PATH}")

    embedding_dim = os.environ.get("EMBEDDING_DIM", _DEFAULT_EMBEDDING_DIM)
    sql_text = _SQL_FILE_PATH.read_text(encoding="utf-8")
    return sql_text.replace("{{EMBEDDING_DIM}}", embedding_dim)


def _compute_hash_martin(sql_text: str) -> str:
    """Return the SHA-256 hex digest of the given SQL text."""
    return hashlib.sha256(sql_text.encode("utf-8")).hexdigest()


def _ensure_migrations_table_martin(conn: PgConnection) -> None:
    """Create the migration-tracking table if it does not exist yet."""
    with conn.cursor() as cur:
        cur.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {_MIGRATIONS_TABLE} (
                id SERIAL PRIMARY KEY,
                sql_hash TEXT NOT NULL,
                applied_at TIMESTAMP NOT NULL DEFAULT NOW()
            );
            """
        )
    conn.commit()


def _get_last_applied_hash_martin(conn: PgConnection) -> str | None:
    """Return the most recently applied schema hash, or None if never applied."""
    with conn.cursor() as cur:
        cur.execute(f"SELECT sql_hash FROM {_MIGRATIONS_TABLE} ORDER BY id DESC LIMIT 1;")
        row = cur.fetchone()
    return row[0] if row else None


def _apply_migration_martin(conn: PgConnection, sql_text: str, sql_hash: str) -> None:
    """Execute the schema SQL and record its hash as applied, in one transaction."""
    with conn.cursor() as cur:
        cur.execute(sql_text)
        cur.execute(
            f"INSERT INTO {_MIGRATIONS_TABLE} (sql_hash) VALUES (%s);",
            (sql_hash,),
        )
    conn.commit()


def run_migrations_martin() -> None:
    """Apply init_rag_db.sql if its content changed since the last run.

    Call this once from main.py before starting the API server. Safe to call
    on every startup — it only re-applies the schema when the SQL file's hash
    differs from the last recorded hash.
    """
    sql_text = _load_sql_martin()
    sql_hash = _compute_hash_martin(sql_text)

    conn = _get_db_connection_martin()
    try:
        _ensure_migrations_table_martin(conn)
        last_hash = _get_last_applied_hash_martin(conn)

        if last_hash == sql_hash:
            logger.info("Schema up to date (hash %s...); skipping migration.", sql_hash[:12])
            return

        logger.info(
            "Schema changed (last=%s..., current=%s...); applying migration.",
            (last_hash or "none")[:12],
            sql_hash[:12],
        )
        _apply_migration_martin(conn, sql_text, sql_hash)
        logger.info("Migration applied successfully.")
    except psycopg2.Error as err:
        conn.rollback()
        raise MigrationError(f"Failed to apply migration: {err}") from err
    finally:
        conn.close()
