"""Idempotent, hash-tracked schema migrations for the RAG pipeline.

Applies each file in _MIGRATION_FILES, in order, on startup. Every file is
idempotent on its own (CREATE TABLE IF NOT EXISTS, CREATE INDEX IF NOT
EXISTS, etc.), so this module only re-executes a given file when its
content hash differs from that file's last-applied hash — each file is
tracked independently, so adding a new migration file never re-runs an
earlier, unchanged one.
"""

from __future__ import annotations

import hashlib
import logging
import os
from pathlib import Path

import psycopg2
from psycopg2.extensions import connection as PgConnection

logger = logging.getLogger(__name__)

_SQL_DIR = Path(__file__).parent
_MIGRATION_FILES = ["init_rag_db.sql", "03_hybrid_search.sql"]
_MIGRATIONS_TABLE = "schema_migrations"
_DEFAULT_EMBEDDING_DIM = "768"


class MigrationError(Exception):
    """Raised when a schema migration cannot be prepared or applied."""


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


def _load_sql_martin(filename: str) -> str:
    """Read one migration file and substitute {{EMBEDDING_DIM}} with the real value.

    Raises:
        MigrationError: the file does not exist next to this module.
    """
    sql_path = _SQL_DIR / filename
    if not sql_path.exists():
        raise MigrationError(f"Schema file not found: {sql_path}")

    embedding_dim = os.environ.get("EMBEDDING_DIM", _DEFAULT_EMBEDDING_DIM)
    sql_text = sql_path.read_text(encoding="utf-8")
    return sql_text.replace("{{EMBEDDING_DIM}}", embedding_dim)


def _compute_hash_martin(sql_text: str) -> str:
    """Return the SHA-256 hex digest of the given SQL text."""
    return hashlib.sha256(sql_text.encode("utf-8")).hexdigest()


def _ensure_migrations_table_martin(conn: PgConnection) -> None:
    """Create the migration-tracking table (and its `filename` column) if needed.

    `filename` defaults existing rows to 'init_rag_db.sql' — accurate for
    every row written before this column existed, since back then the
    table only ever tracked that one file.
    """
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
        cur.execute(
            f"""
            ALTER TABLE {_MIGRATIONS_TABLE}
            ADD COLUMN IF NOT EXISTS filename TEXT NOT NULL DEFAULT 'init_rag_db.sql';
            """
        )
    conn.commit()


def _get_last_applied_hash_martin(conn: PgConnection, filename: str) -> str | None:
    """Return the most recently applied hash for filename, or None if never applied."""
    with conn.cursor() as cur:
        cur.execute(
            f"SELECT sql_hash FROM {_MIGRATIONS_TABLE} WHERE filename = %s "
            "ORDER BY id DESC LIMIT 1;",
            (filename,),
        )
        row = cur.fetchone()
    return row[0] if row else None


def _apply_migration_martin(conn: PgConnection, sql_text: str, sql_hash: str, filename: str) -> None:
    """Execute one migration file's SQL and record its hash as applied, in one transaction."""
    with conn.cursor() as cur:
        cur.execute(sql_text)
        cur.execute(
            f"INSERT INTO {_MIGRATIONS_TABLE} (sql_hash, filename) VALUES (%s, %s);",
            (sql_hash, filename),
        )
    conn.commit()


def _apply_one_file_martin(conn: PgConnection, filename: str) -> None:
    """Apply filename if its content changed since it was last applied."""
    sql_text = _load_sql_martin(filename)
    sql_hash = _compute_hash_martin(sql_text)
    last_hash = _get_last_applied_hash_martin(conn, filename)

    if last_hash == sql_hash:
        logger.info("%s up to date (hash %s...); skipping migration.", filename, sql_hash[:12])
        return

    logger.info(
        "%s changed (last=%s..., current=%s...); applying migration.",
        filename,
        (last_hash or "none")[:12],
        sql_hash[:12],
    )
    _apply_migration_martin(conn, sql_text, sql_hash, filename)
    logger.info("%s applied successfully.", filename)


def run_migrations_martin() -> None:
    """Apply each file in _MIGRATION_FILES whose content changed since last run.

    Call this once from main.py before starting the API server. Safe to call
    on every startup — each file only re-applies when its own hash differs
    from its own last recorded hash.
    """
    conn = _get_db_connection_martin()
    try:
        _ensure_migrations_table_martin(conn)
        for filename in _MIGRATION_FILES:
            _apply_one_file_martin(conn, filename)
    except psycopg2.Error as err:
        conn.rollback()
        raise MigrationError(f"Failed to apply migration: {err}") from err
    finally:
        conn.close()
