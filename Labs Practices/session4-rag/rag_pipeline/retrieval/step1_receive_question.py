"""Receive and validate the incoming question payload.

Task (see rag-structure.md > retrieval/): take {"question": str}, trim it,
reject empty/missing input.
"""

from __future__ import annotations


def receive_question_martin(payload: dict[str, str]) -> str:
    """Return the validated question string from the request payload."""
    question = (payload.get("question") or "").strip()
    if not question:
        raise ValueError("Missing or empty 'question'")
    return question
