"""Call llama3.1 with the final prompt.

Task (see rag-structure.md > retrieval/): call config/llm_setup.py's
chat_martin with the built prompt.
"""

from __future__ import annotations

from config.env_config import RagConfig
from config.llm_setup import chat_martin


def call_llm_martin(config: RagConfig, prompt: str) -> str:
    """Return llama3.1's raw answer text for the given prompt."""
    return chat_martin(config, prompt)
