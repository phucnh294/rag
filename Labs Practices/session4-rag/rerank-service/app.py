"""Minimal HTTP wrapper around a local cross-encoder reranker model.

POST /rerank {"query": str, "documents": list[str]} -> {"scores": list[float]}
One score per document, same order as the input list, higher = more relevant.
"""

from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel
from sentence_transformers import CrossEncoder

MODEL_NAME = "cross-encoder/ms-marco-MiniLM-L-6-v2"

app = FastAPI(title="Rerank Service")
_model = CrossEncoder(MODEL_NAME)


class RerankRequest(BaseModel):
    query: str
    documents: list[str]


class RerankResponse(BaseModel):
    scores: list[float]


@app.post("/rerank")
def rerank(request: RerankRequest) -> RerankResponse:
    if not request.documents:
        return RerankResponse(scores=[])
    pairs = [(request.query, document) for document in request.documents]
    scores = _model.predict(pairs)
    return RerankResponse(scores=[float(score) for score in scores])


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "model": MODEL_NAME}
