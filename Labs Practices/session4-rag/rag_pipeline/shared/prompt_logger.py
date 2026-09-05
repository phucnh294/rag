"""Audit log of every question, its full LLM request, and the model's answer.

Distinct from shared/logger.py's general application logging: this records
the exact input/output boundary with the LLM for each /chat request - the
system instructions (rules), the retrieved context, the user's question, the
provider/model that received it, the complete prompt text actually sent, and
the raw answer returned - so the system's actual behavior can be verified
directly instead of inferred from the final API response alone.

One file per day (PROMPT_LOG_DIR/prompt_log_YYYY-MM-DD.md), one timestamped
Markdown entry per request, append-only.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

_PROMPT_LOG_DIR = Path(__file__).resolve().parent.parent / "prompt_logs"


def log_prompt_martin(
    question: str,
    system_prompt: str,
    context: str,
    full_prompt: str,
    provider: str,
    model: str,
    raw_request: dict[str, Any],
    answer: str,
) -> None:
    """Append one timestamped record of a full LLM request/response to today's log.

    raw_request is the exact JSON body posted to the provider's API (see
    config/llm_setup.py) — never includes secrets; the Gemini API key
    travels as a URL param, not in this body.
    """
    _PROMPT_LOG_DIR.mkdir(parents=True, exist_ok=True)
    now = datetime.now()
    log_file = _PROMPT_LOG_DIR / f"prompt_log_{now:%Y-%m-%d}.md"

    entry = (
        f"## {now:%Y-%m-%d %H:%M:%S}\n\n"
        f"**Provider / model:** {provider} / {model}\n\n"
        f"**User input (question):**\n{question}\n\n"
        f"**System prompt (rules):**\n```\n{system_prompt}\n```\n\n"
        f"**Context (retrieved chunks assembled):**\n```\n{context}\n```\n\n"
        f"**Full prompt actually sent to model:**\n```\n{full_prompt}\n```\n\n"
        f"**Raw request body sent to the model API:**\n```json\n"
        f"{json.dumps(raw_request, indent=2, ensure_ascii=False)}\n```\n\n"
        f"**Model response (after):**\n```\n{answer}\n```\n\n"
        "---\n\n"
    )
    with log_file.open("a", encoding="utf-8") as f:
        f.write(entry)
