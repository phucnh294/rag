"""Postgres connection helper shared by indexing and retrieval.

Task (see rag-structure.md > config/): open a Postgres connection (or a
small pool) using RagConfig. Used by indexing/step7, step8, and
retrieval/step4.
"""

from __future__ import annotations

from typing import Any

import psycopg2

from config.env_config import RagConfig


def get_connection_martin(config: RagConfig) -> Any:
    """Open a Postgres connection using the given config.

    Returns:
        A psycopg2 connection (or equivalent) ready for use.
    """
    return psycopg2.connect(
        host=config.postgres_host,
        port=config.postgres_port,
        user=config.postgres_user,
        password=config.postgres_password,
        dbname=config.postgres_db,
    )
