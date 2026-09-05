---
title: Reranker Fooled by Distractor Documents
date: 2026-09-02
type: qanda
area: rag-pipeline-retrieval
status: implementation-complete
session_id: n/a
duration: ~120min
issue_type: bug
severity: high
resolution_date: 2026-09-02
tags: [rag-pipeline, reranking, cross-encoder, metadata-filtering, status, area]
keywords: [ms-marco-MiniLM-L-6-v2, distractor, status=current, include_reference, area scoping, ON CONFLICT source_path]
related: [rag-ai-local/functionality-docs/09022026/03_metadata-filtering-problems-and-tradeoffs.md, rag-ai-local/functionality-docs/09022026/01_reranking-service-and-toggle.md]
---

## TL;DR
- **What:** `POST /chat` answered "I don't know" to "How many PTO days does a full-time employee receive per year?" with reranking on, despite the correct document being retrievable, and correct with reranking off.
- **Why:** The cross-encoder reranker (`ms-marco-MiniLM-L-6-v2`) scored keyword-stuffed decoy documents above the actual answer.
- **Where:** `retrieval/step6_reranking.py` (the reranker itself, unchanged), fixed via `retrieval/step5_metadata_filter.py` (new area-scoped `status=current` filtering).
- **Impact:** Root-caused via the retrieval debug panel's `before_rerank`/`after_rerank` score breakdown; fixed with document-level authoritative-source tagging, without breaking a second, previously-working question.

## Q1: Why did the cross-encoder reranker (`ms-marco-MiniLM-L-6-v2`) score `04_archived_pto_policy.md` and several "distractor" FAQ pages higher than the document that actually answers the question?

**Answer:** The decoy documents were written to contain the literal question text ("How many PTO days does a full-time employee receive per year?") verbatim, while explicitly disclaiming "this does **not** define the entitlement." A cross-encoder scores lexical/topical overlap between the query and the passage — it has no mechanism to parse a disclaimer sentence as a negative signal. A document that *quotes the question* therefore outscores the document that *answers it*.

**Evidence:**
```
before_rerank (vector similarity): 02_correct_leave_policy.md scored 0.7037 (rank 5)
after_rerank (cross-encoder):      03_holiday_number_distractor.md  5.87
                                    01_keyword_distractor.md         5.82
                                    07_manager_planning_distractor.md 3.40
                                    05_balance_distractor.md          3.32
                                    04_archived_pto_policy.md         2.05
                                    (02_correct_leave_policy.md not in top 5 — pushed out entirely)
```

**Root cause:** Cross-encoder relevance scoring cannot distinguish "topically similar" from "actually correct" — a known limitation against keyword-stuffed adversarial content.
**Fix:** N/A at the reranker level (this is inherent to the model) — fixed upstream by excluding this kind of content from ever reaching the reranker; see Q2/Q3.

## Q2: Why didn't filtering out `status="archived"` fix the PTO-days question?

**Answer:** Of the 4 documents that outranked the correct answer, none were archived — they were ordinary-looking FAQ/guide pages (`01_keyword_distractor.md`, `03_holiday_number_distractor.md`, `05_balance_distractor.md`, `07_manager_planning_distractor.md`). `04_archived_pto_policy.md` only barely edged out the correct doc for the *last* spot in the top-5. Excluding only the archived document would have left the actual four culprits fully in play.

**Evidence:** See the `after_rerank` ranking in Q1 — 4 of the top 5 results are non-archived distractors, not the archived doc.

**Root cause:** The failure mode isn't "archived content is bad," it's "any content that's topically similar but doesn't actually answer the question can outrank the real answer" — a broader category than `status=archived` alone.
**Fix:** `retrieval/step5_metadata_filter.py` — implemented `status="current"` as a positive/authoritative marker instead of trying to enumerate every kind of "bad" content by exclusion. See `03_metadata-filtering-problems-and-tradeoffs.md` for the full options considered.

## Q3: After tagging `02_correct_leave_policy.md` as `status="current"` (fixing the PTO-days question), why did a different, previously-working question — "How do I submit a PTO request?" — start returning "I don't know" too?

**Answer:** The metadata filter's first version restricted retrieval to `status="current"` candidates *globally*, whenever any existed in the pool — with no regard for whether the current-tagged document was actually relevant to the specific question asked. `02_correct_leave_policy.md`'s vector embedding is broadly similar to any PTO-related question (not just "how many days"), so it still appeared in the candidate pool for the request-submission question and, being the only `current`-tagged candidate, crowded out `06_request_process_distractor.md` — the document that actually answers *that* question.

**Evidence:**
```
Before fix: "How do I submit a PTO request?" → "I don't know."
            sources: ["/app/input/02_correct_leave_policy.md"]  (wrong document for this question)
```

**Root cause:** The filter had no concept of topic/area scoping — a `current` tag anywhere in the pool overrode retrieval for every question, not just questions about that document's actual topic.
**Fix:** `retrieval/step5_metadata_filter.py` — added `area`-scoped restriction: a reference-only candidate is only excluded if it's untagged or shares a `current` document's area; an explicitly different-area candidate survives. Also tagged `06_request_process_distractor.md` as `status="current", area="leave-request-process"` (distinct from `02_correct_leave_policy.md`'s `area="leave-entitlement"`), since fixing this required curating *that* topic's authoritative source too, not just changing the filter logic.
```
After fix: "How do I submit a PTO request?" → correct step-by-step answer, sourced from 06_request_process_distractor.md
           "How many PTO days...?" → still correct ("18 days") — original fix unaffected
```

## Q4: Why did re-uploading a document's content (extracted from Postgres) to add `status`/`area` tags create a *duplicate* row instead of updating the existing one?

**Answer:** `store_document_martin`'s upsert key is `source_path`, which `shared/file_utils.py:save_upload_martin` derives from the **uploaded file's filename**. When re-uploading via `curl -F "file=@/tmp/06_request_process.md"` (a Postgres content extract saved to a temp file), curl takes the multipart filename from the local temp file's path (`06_request_process.md`), not the original document's name (`06_request_process_distractor.md`). The upsert's `ON CONFLICT (source_path)` never matched, since `/app/input/06_request_process.md` and `/app/input/06_request_process_distractor.md` are different `source_path` values — so a brand new row was inserted instead.

**Evidence:**
```
SELECT source_path FROM rag_documents;
-- showed both 06_request_process_distractor.md (old, untagged) AND
-- 06_request_process.md (new, tagged) — 8 rows instead of 7
```

**Root cause:** curl's `-F "file=@path"` always names the upload after the local file path's basename; there's no implicit way to "re-upload as" a different filename without either the `;filename=` multipart parameter (which errored in this environment, exit code 26) or renaming the local file first.
**Fix:** Deleted the accidental duplicate row (`DELETE FROM rag_documents WHERE source_path = '/app/input/06_request_process.md'` — cascades to its chunks/embeddings), renamed the local temp file to match the original document's exact name (`cp /tmp/06_request_process.md /tmp/06_request_process_distractor.md`), then re-uploaded — the upsert matched correctly on the second attempt. General lesson: when re-uploading extracted content to update tags on an existing document, always verify the row count in `rag_documents` afterward to catch an accidental new insert.
