"""Audit log of every question, its full LLM prompt, and the model's answer.

Distinct from shared/logger.py's general application logging: this records
the exact input/output boundary with the LLM for each /chat request — the
question received, the complete prompt built before the model call, and the
raw answer returned after — so the system's actual behavior can be verified
directly instead of inferred from the final API response alone.

One file per day (PROMPT_LOG_DIR/prompt_log_YYYY-MM-DD.md), one timestamped
Markdown entry per request, append-only.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

_PROMPT_LOG_DIR = Path(__file__).resolve().parent.parent / "prompt_logs"


def log_prompt_martin(question: str, prompt: str, answer: str) -> None:
    """Append one timestamped question/prompt/answer record to today's log file."""
    _PROMPT_LOG_DIR.mkdir(parents=True, exist_ok=True)
    now = datetime.now()
    log_file = _PROMPT_LOG_DIR / f"prompt_log_{now:%Y-%m-%d}.md"

    entry = (
        f"## {now:%Y-%m-%d %H:%M:%S}\n\n"
        f"**User input (question):**\n{question}\n\n"
        f"**Prompt sent to model (before):**\n```\n{prompt}\n```\n\n"
        f"**Model response (after):**\n```\n{answer}\n```\n\n"
        "---\n\n"
    )
    with log_file.open("a", encoding="utf-8") as f:
        f.write(entry)
