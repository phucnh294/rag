"""Build the final prompt sent to llama3.1.

Task (see rag-structure.md > retrieval/): system instructions + context
block + the user's question, in the shape llama3.1 expects.
"""

from __future__ import annotations

_SYSTEM_INSTRUCTIONS = (
    "You are a helpful assistant answering questions using only the context "
    "provided below. If the context does not contain the answer, say you "
    "don't know instead of guessing."
)


def build_prompt_martin(context: str, question: str) -> str:
    """Return the final prompt string for the chat model."""
    return (
        f"{_SYSTEM_INSTRUCTIONS}\n\n"
        f"Context:\n{context}\n\n"
        f"Question: {question}\n"
        "Answer:"
    )
