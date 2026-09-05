"""Process entry point: apply schema migrations, then start the API server.

Wiring only — no RAG logic lives here. See rag-structure.md for the
file-by-file task breakdown of everything under config/, indexing/,
retrieval/, api/, and shared/.
"""

from __future__ import annotations

import logging
import os

import uvicorn

from sql.migrations import run_migrations_martin

logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)


def main_martin() -> None:
    """Run migrations, then start the FastAPI app defined in api/main.py."""
    logger.info("Applying schema migrations...")
    run_migrations_martin()

    logger.info("Starting API server on :8000")
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main_martin()
