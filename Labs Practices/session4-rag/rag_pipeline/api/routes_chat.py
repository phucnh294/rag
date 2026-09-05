"""POST /chat — answer a question using the retrieval process.

Task (see rag-structure.md > api/): accept {"question": str}, call
retrieval.retrieval_runner, return its {"answer", "sources"} dict directly.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any

import psycopg2
import requests
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from config.env_config import load_config_martin
from retrieval.retrieval_runner import run_retrieval_martin

router = APIRouter()


class ChatRequest(BaseModel):
    """Request body for POST /chat."""

    question: str
    rerank: bool | None = None  # None = use the server's RERANK_ENABLED default
    hybrid: bool | None = None  # None = use the server's HYBRID_SEARCH_ENABLED default
    include_reference: bool = False  # True = skip the status="current" restriction


@router.post("/chat")
async def chat_martin(request: ChatRequest) -> dict[str, Any]:
    """Answer the question via the retrieval process. Return {"answer", "sources"}."""
    config = load_config_martin()
    if request.rerank is not None:
        config = replace(config, rerank_enabled=request.rerank)
    if request.hybrid is not None:
        config = replace(config, hybrid_enabled=request.hybrid)
    try:
        return run_retrieval_martin(
            config, {"question": request.question}, include_reference=request.include_reference
        )
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err)) from err
    except requests.exceptions.Timeout as err:
        raise HTTPException(status_code=504, detail=f"LLM request timed out: {err}") from err
    except requests.exceptions.RequestException as err:
        raise HTTPException(status_code=502, detail=f"LLM request failed: {err}") from err
    except psycopg2.Error as err:
        raise HTTPException(status_code=502, detail=f"Database error: {err}") from err
