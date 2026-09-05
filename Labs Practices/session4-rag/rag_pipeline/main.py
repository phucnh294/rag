"""Process entry point: apply schema migrations, then start the API server.

Wiring only — no RAG logic lives here. See rag-structure.md for the
file-by-file task breakdown of everything under config/, indexing/,
retrieval/, api/, and shared/.
"""

from __future__ import annotations

import logging
import os

import uvicorn
from dotenv import load_dotenv

load_dotenv()  # populate os.environ from .env when running locally (no-op under Docker,
# where env_file already injects vars before this process starts)

from sql.migrations import run_migrations_martin  # noqa: E402 (must follow load_dotenv())

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
