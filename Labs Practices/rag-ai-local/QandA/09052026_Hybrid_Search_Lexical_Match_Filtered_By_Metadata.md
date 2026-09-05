---
title: Hybrid Search Lexical Match Filtered by Existing Metadata Filter
date: 2026-09-05
type: qanda
area: rag-pipeline-retrieval
status: implementation-complete
session_id: n/a
duration: ~20min
issue_type: design-question
severity: low
resolution_date: 2026-09-05
tags: [rag-pipeline, hybrid-search, full-text-search, metadata-filtering, rrf]
keywords: [ts_rank, websearch_to_tsquery, found_by, status=current, reciprocal_rank_fusion_martin, include_reference]
related: [rag-ai-local/functionality-docs/09052026/03_hybrid-search-rrf.md, rag-ai-local/functionality-docs/09022026/03_metadata-filtering-problems-and-tradeoffs.md]
---

## TL;DR
- **What:** With hybrid search enabled, a direct Postgres full-text query found a strong lexical match (`01_keyword_distractor.md`) for the PTO-days question, but the live `/chat` response never showed it in `retrieval_scores.before_rerank`.
- **Why:** Needed to confirm whether hybrid search's fusion logic was actually running, or silently failing to surface a real match.
- **Where:** `retrieval/hybrid/lexical.py`, `retrieval/hybrid/fusion.py`, `retrieval/step5_metadata_filter.py`.
- **Impact:** Confirmed working as designed — fusion did include the lexical match, and the pre-existing metadata filter (from an earlier session) correctly excluded it downstream before it could reach the answer. Not a hybrid-search bug.

## Q1: Why did a direct `ts_rank`/`websearch_to_tsquery` query find `01_keyword_distractor.md` for "How many PTO days does a full-time employee receive per year?", but `/chat` with `{"hybrid": true}` (no `include_reference`) never showed it in `retrieval_scores.before_rerank`?

**Answer:** The lexical match was found and correctly fused into the candidate pool (confirmed via `include_reference: true`, which bypasses the metadata filter) — it just never survived past `step5_metadata_filter.py`, which runs *after* fusion and *before* the debug-panel data (`before_rerank`) is captured. `01_keyword_distractor.md` is untagged (`status`/`area` both `NULL`), and the pool also contains `02_correct_leave_policy.md` (`status="current"`, `area="leave-entitlement"`) — so the existing area-scoped filter (implemented in the 09-02 session, see related doc) excludes the untagged distractor as a same-topic reference-only chunk, regardless of how it was originally found (vector, lexical, or both).

**Evidence:**
```
# Direct SQL — confirms the lexical match exists and scores highly:
SELECT d.source_path, ts_rank(...) AS score
FROM rag_chunks c JOIN rag_documents d ON d.id = c.document_id
WHERE c.content_tsv @@ websearch_to_tsquery('english', 'How many PTO days...?')
ORDER BY score DESC;
-> /app/input/01_keyword_distractor.md | 0.9999997

# /chat with hybrid:true, include_reference:false (default):
-> before_rerank: [02_correct_leave_policy.md, 06_request_process_distractor.md]
   (01_keyword_distractor.md absent)

# /chat with hybrid:true, include_reference:true (bypasses the metadata filter):
-> before_rerank[0]: 01_keyword_distractor.md, score=0.0328, found_by="both"
   (highest RRF score of all 7 candidates — confirms fusion DID include it)
```

**Root cause:** Two independent, correctly-functioning stages composing in sequence — fusion doesn't know about (and shouldn't know about) metadata filtering, and the metadata filter doesn't distinguish "found by vector" from "found by lexical" (nor should it; a same-topic decoy is a same-topic decoy regardless of how retrieval found it).
**Fix:** N/A — no code change; this is the correct interaction of two independent stages. Confirmed by re-running with `include_reference: true` to observe the pipeline's state *before* the metadata filter runs.

## Q2: Does this mean hybrid search's `found_by` field is unreliable for debugging when the metadata filter is also active?

**Answer:** No — `found_by` accurately reflects fusion's own output at the point fusion runs; it just reflects a snapshot *before* the metadata filter's exclusions, same as `before_rerank` always has for reranking. Anyone debugging "why didn't hybrid search help here" needs to add `include_reference: true` to see the full fused pool, exactly the same way anyone debugging "why did reranking drop a candidate" already needed to check `before_rerank` vs. `after_rerank`. This is a pre-existing pattern in this pipeline's debug tooling, not something new introduced by hybrid search.

**Evidence:** See Q1's evidence block — `found_by="both"` on `01_keyword_distractor.md` was accurate and consistent between the `include_reference:true` and direct-SQL checks; it just wasn't visible in the *filtered* (`include_reference:false`) response, which was never claiming to show the pre-filter pool in the first place.

**Root cause:** N/A (not a bug) — a debugging/observability nuance rather than a defect.
**Fix:** N/A. Documented here so a future session doesn't re-investigate the same non-bug.
