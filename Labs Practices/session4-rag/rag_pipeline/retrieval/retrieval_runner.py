"""Orchestrate the retrieval process (steps 1-10) for one question.

Task (see rag-structure.md > retrieval/): wire step1..step10 together and
return the shaped response dict for the API.
"""

from __future__ import annotations

from typing import Any

from config.db_connection import get_connection_martin
from config.env_config import RagConfig
from retrieval.step1_receive_question import receive_question_martin
from retrieval.step2_normalize_question import normalize_question_martin
from retrieval.step3_embed_question import embed_question_martin
from retrieval.step4_similarity_search import similarity_search_martin
from retrieval.step5_metadata_filter import filter_by_metadata_martin
from retrieval.step6_reranking import rerank_chunks_martin
from retrieval.step7_context_assembly import assemble_context_martin
from retrieval.step8_prompt_building import build_prompt_martin
from retrieval.step9_llm_call import call_llm_martin
from retrieval.step10_response import build_response_martin
from shared.logger import get_logger_martin

logger = get_logger_martin(__name__)

# Retrieve a larger candidate pool than the final context size so the
# reranker actually has something to reorder, then truncate after rerank.
_RERANK_CANDIDATE_POOL = 10
_RERANK_TOP_N = 10


def _log_ranking_martin(label: str, chunks: list[Any]) -> None:
    """Log each chunk's source_path + score, in order, for before/after comparison."""
    ranking = [(chunk["source_path"], round(chunk["score"], 4)) for chunk in chunks]
    logger.info("%s ranking (top %d): %s", label, len(ranking), ranking)


def run_retrieval_martin(
    config: RagConfig, payload: dict[str, str], include_reference: bool = False
) -> dict[str, Any]:
    """Answer one question end-to-end. Return {"answer", "sources"}."""
    question = receive_question_martin(payload)
    question = normalize_question_martin(question)
    question_embedding = embed_question_martin(config, question)

    top_k = _RERANK_CANDIDATE_POOL if config.rerank_enabled else _RERANK_TOP_N
    conn = get_connection_martin(config)
    try:
        candidates = similarity_search_martin(conn, question_embedding, top_k=top_k)
    finally:
        conn.close()

    filtered = filter_by_metadata_martin(candidates, include_reference=include_reference)
    restricted_to_current = len(filtered) < len(candidates)
    _log_ranking_martin("vector-search", filtered[:_RERANK_TOP_N])

    if config.rerank_enabled:
        reranked = rerank_chunks_martin(config, question, filtered, top_n=_RERANK_TOP_N)
        _log_ranking_martin("reranked", reranked)
    else:
        reranked = filtered[:_RERANK_TOP_N]

    context = assemble_context_martin(reranked)
    prompt = build_prompt_martin(context, question)
    answer = call_llm_martin(config, prompt)

    return build_response_martin(
        answer,
        reranked,
        rerank_applied=config.rerank_enabled,
        before_rerank=filtered,
        excluded_count=len(candidates) - len(filtered),
        restricted_to_current=restricted_to_current,
    )
