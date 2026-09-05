---
title: Metadata Filtering — Problems, Solutions, and Trade-offs
date: 2026-09-02
type: functionality
area: rag-pipeline-retrieval
status: implementation-complete
session_id: n/a
duration: ~120min
files: [Labs Practices/session4-rag/rag_pipeline/indexing/step5_metadata_extraction.py, Labs Practices/session4-rag/rag_pipeline/indexing/step7_store_documents.py, Labs Practices/session4-rag/rag_pipeline/indexing/index_runner.py, Labs Practices/session4-rag/rag_pipeline/api/routes_upload.py, Labs Practices/session4-rag/rag_pipeline/retrieval/step4_similarity_search.py, Labs Practices/session4-rag/rag_pipeline/retrieval/step5_metadata_filter.py, Labs Practices/session4-rag/rag_pipeline/retrieval/step6_reranking.py, Labs Practices/session4-rag/rag_pipeline/retrieval/retrieval_runner.py, Labs Practices/session4-rag/rag_pipeline/retrieval/step10_response.py, Labs Practices/session4-rag/rag_pipeline/api/routes_chat.py, Labs Practices/session4-rag/rag_pipeline/ui/index.html]
version: 1
last_updated: 2026-09-02
extraction_method: pair-session
tags: [rag-pipeline, metadata-filtering, reranking, lab2, status, area]
keywords: [status=current, include_reference, area scoping, distractor documents, cross-encoder failure]
related: [rag-ai-local/functionality-docs/09022026/01_reranking-service-and-toggle.md, rag-ai-local/QandA/09022026_Reranker_Fooled_By_Distractor_Documents.md]
---

## TL;DR
- **What:** Three chained problems, found by actually using the reranker on a real eval corpus, each requiring a different fix: the cross-encoder loses to keyword-stuffed decoys, an archived-only exclusion filter doesn't cover that, and a naive "prefer curated content" filter over-applies across unrelated topics. Solved with area-scoped `status=current` filtering plus an explicit override.
- **Why:** Reranking (implemented earlier the same day) was found to actively make answers *worse* on a real question — the whole point of adding it was answer quality, so this had to be root-caused and fixed, not shipped as-is.
- **Where:** `indexing/step5_metadata_extraction.py`, `indexing/step7_store_documents.py`, `retrieval/step4_similarity_search.py`, `retrieval/step5_metadata_filter.py`, plus threading `status`/`area` through the rest of the indexing and retrieval pipelines.
- **Impact:** Both the original bug (wrong PTO-days answer) and a regression this fix introduced (a different, previously-working question started failing) are now fixed and verified together, without either one breaking the other.

## Problem 1: The reranker prefers keyword-stuffed decoys over the actual answer

Asking *"How many PTO days does a full-time employee receive per year?"* against a 7-document corpus (1 correct policy doc, 1 archived doc, 5 "distractor" docs deliberately written to test RAG robustness) returned **"I don't know."** with reranking on, but the correct answer ("18 days") with reranking off.

**Root cause:** `02_correct_leave_policy.md` ranked 5th by vector similarity (`0.7037`) — good enough to reach the reranker's candidate pool. But the cross-encoder (`cross-encoder/ms-marco-MiniLM-L-6-v2`) scored 4 *other* documents higher (`5.87`, `5.82`, `3.40`, `3.32`) — decoy pages that literally repeat the question text ("How many PTO days does a full-time employee receive per year?") while explicitly disclaiming "this does **not** define the entitlement." The cross-encoder matches on lexical/topical overlap with the query and has no way to parse that disclaimer as a negative signal, so a document that *quotes the question* outscores the document that *answers it*. The correct doc got pushed out of the final top-5 entirely.

This is not a bug in the implementation — it's a real, well-known limitation of small general-purpose cross-encoders against adversarial/keyword-stuffed content, and it directly reproduces exactly what this test corpus appears designed to catch.

## Problem 2: An archived-only filter doesn't fix it

The first fix considered was narrow: add a `status="archived"` filter to exclude `04_archived_pto_policy.md`. **This was checked against the actual data before implementing it, and rejected** — of the 4 documents outranking the correct answer, **none were archived**. They're ordinary-looking FAQ/guide pages. Excluding only the archived doc would have left all 4 real culprits in place; the bug would not have been fixed.

### Options considered
| Option | Verdict |
|---|---|
| **A — `status=archived` exclusion only** | Rejected: doesn't address the actual failure (see above) — the archived doc wasn't the deciding factor. |
| **B — Broader "authoritative content" status** (`status=current` on the *correct* doc, prefer it whenever present) | **Chosen.** Doesn't require detecting what's individually wrong with every kind of decoy — just requires marking what's *right*. |
| **C — Try a stronger/larger reranker model** | Not chosen for this pass: no guarantee it fixes an adversarial-content problem (still fundamentally judging text relevance, not fact-correctness), and doesn't address that the corpus can always add a more convincing decoy. Left as a possible future option, not implemented. |
| **D — Increase `top_n` after reranking** | Not chosen: band-aid that dilutes context with more irrelevant chunks and only reduces (doesn't eliminate) the chance of losing the correct doc. |

## Problem 3: A global "prefer current" filter breaks unrelated questions

With Option B implemented (`status=current` tagging `02_correct_leave_policy.md`, filter restricts to current-tagged candidates whenever any exist), the PTO-days question was fixed — **but a regression test caught a new failure**: *"How do I submit a PTO request?"* (correctly answerable by `06_request_process_distractor.md`, a "distractor" in name only — its content is genuinely correct for its own topic) also started returning "I don't know."

**Root cause:** `02_correct_leave_policy.md`'s vector embedding is broadly similar to any PTO-related question, not just "how many days" — so it still lands in the candidate pool for the request-submission question too. The filter's rule ("if any candidate is `status=current`, restrict to only those") is **topic-blind**: it applied the leave-policy doc's authority to a question it has nothing to do with, crowding out the actually-relevant document.

### Options considered
| Option | Verdict |
|---|---|
| **Add `area` tagging, scope the restriction to matching areas** | **Chosen.** Matches `rag-structure.md`'s original Lab2 spec intent ("pre-filter by area/status/tags") — properly scopes the override instead of applying it corpus-wide. |
| **Score-margin fallback** (only restrict if the current doc's vector score is close to the top score) | Not chosen: simpler, no new tagging, but a fragile heuristic — "close" is an arbitrary threshold that could misfire on other queries in unpredictable ways. |
| **Leave the global behavior as-is** | Not chosen once the regression was demonstrated — fixing the reported bug while silently breaking a different, previously-working question is not an acceptable trade.

## The final rule (`retrieval/step5_metadata_filter.py`)

```python
def filter_by_metadata_martin(candidates, include_reference=False):
    if include_reference:
        return candidates
    current_areas = {c.get("area") for c in candidates if c.get("status") == "current"}
    if not current_areas:
        return candidates
    def is_same_topic_reference(chunk):
        if chunk.get("status") == "current":
            return False
        return chunk.get("area") is None or chunk.get("area") in current_areas
    return [c for c in candidates if not is_same_topic_reference(c)]
```

Reference-only candidates are dropped only if they're **untagged** (can't prove they're about something else — conservative default, matches the pre-area-scoping behavior for anything not explicitly tagged) or **share a `current` doc's area**. A reference-only candidate with an explicit, *different* area survives untouched. This means fixing a second topic (e.g. the request-submission question) requires **also** tagging its own authoritative document — `06_request_process_distractor.md` was tagged `status=current, area=leave-request-process` for exactly this reason, alongside `02_correct_leave_policy.md`'s `status=current, area=leave-entitlement`.

**Trade-off accepted:** this is manual curation work — every distinct topic needs its own explicitly-tagged authoritative document to benefit from this filter. An un-curated topic (no `current` doc anywhere in its candidate pool) falls back to full unfiltered retrieval automatically, so nothing regresses to zero results — but it also gets none of this protection until someone tags something.

## The override: `include_reference`

`include_reference: true` (API) / "Include reference-only" checkbox (UI) skips the restriction entirely, returning the full unfiltered pool — this is deliberately "archived/decoy content can still be used in some case," matching the same opt-in shape as the earlier `rerank` toggle. Verified: re-running the PTO-days question with `include_reference: true` reproduces the *original* bug exactly (all 5 non-current documents back as candidates, "I don't know" again) — proving the override genuinely restores unfiltered behavior rather than partially filtering.

## Tagging mechanism

Two ways to set `status`/`area`, since this test corpus has **no YAML frontmatter at all** (confirmed via `SELECT raw_content FROM rag_documents` — no leading `---` blocks) despite `rag-structure.md`'s Lab2 spec assuming frontmatter-based tagging:
1. **Real frontmatter** (`indexing/step5_metadata_extraction.py`, `yaml.safe_load`) — works for documents that have it, like this project's own `rag-ai-local` corpus.
2. **Explicit `POST /upload` form fields** (`status`, `area`) — added specifically because this corpus has no frontmatter and the user needed to tag it without hand-editing files. Upload-time values win over frontmatter when both are present (`indexing/index_runner.py`: `status or frontmatter_metadata.get("status")`).

## Verification

```
# Tag the two authoritative docs (re-upload via POST /upload, ON CONFLICT upsert updates in place)
curl -F "file=@02_correct_leave_policy.md" -F "status=current" -F "area=leave-entitlement" http://localhost:8000/upload
curl -F "file=@06_request_process_distractor.md" -F "status=current" -F "area=leave-request-process" http://localhost:8000/upload

# Original bug — now fixed
curl -X POST http://localhost:8000/chat -d '{"question": "How many PTO days does a full-time employee receive per year?"}'
→ "18 paid personal leave days per calendar year", excluded_count: 5, restricted_to_current: true

# Regression this fix introduced — now also fixed
curl -X POST http://localhost:8000/chat -d '{"question": "How do I submit a PTO request?"}'
→ correct step-by-step answer using the request-process doc, not "I don't know"

# Override still works (reproduces the original bug on demand)
curl -X POST http://localhost:8000/chat -d '{"question": "How many PTO days...?", "include_reference": true}'
→ "I don't know.", excluded_count: 0
```

One real mistake made and caught during this verification, worth recording: re-uploading `06_request_process_distractor.md`'s content from a Postgres extract via `curl -F "file=@/tmp/06_request_process.md"` created a **new** document row (`/app/input/06_request_process.md`) instead of updating the existing one, because the upsert key is `source_path`, which `save_upload_martin` derives from the uploaded file's **filename** — and curl takes the filename from the local temp file path, not the original document's name. Caught via `SELECT source_path FROM rag_documents` showing 8 rows instead of 7; fixed by deleting the duplicate and renaming the local temp file to match the original before re-uploading.
