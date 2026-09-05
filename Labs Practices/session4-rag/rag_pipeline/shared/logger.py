"""One place that configures the logging module for the whole pipeline.

Task (see rag-structure.md > shared/): configure level from env, a
consistent format — imported by every other module instead of each one
configuring logging itself.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path

_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"
_LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
_MAX_BYTES = 5 * 1024 * 1024  # 5MB per file, per task ("format file by date with maximum 5mb")
_BACKUP_COUNT = 5

_configured = False


def _configure_root_martin() -> None:
    """Attach a console handler and a rotating, date-named file handler once."""
    global _configured
    if _configured:
        return

    level = os.environ.get("LOG_LEVEL", "INFO")
    formatter = logging.Formatter(_FORMAT)

    _LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_file = _LOG_DIR / f"rag_app_{datetime.now():%Y-%m-%d}.log"
    file_handler = RotatingFileHandler(
        log_file, maxBytes=_MAX_BYTES, backupCount=_BACKUP_COUNT, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(level)
    root.addHandler(file_handler)
    root.addHandler(console_handler)
    _configured = True


def get_logger_martin(name: str) -> logging.Logger:
    """Return a configured logger for the given module name."""
    _configure_root_martin()
    return logging.getLogger(name)
