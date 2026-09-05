---
title: "Handoff: Reranking + Metadata Filtering Complete"
date: 2026-09-02
type: session-handoff
area: rag-pipeline-retrieval
status: implementation-complete
session_id: n/a
next_action: "Consider tagging more topics (status=current + area) as the corpus grows — untagged topics get zero protection from the reranker's decoy-susceptibility until curated. Otherwise, next open items are the carried-forward ones below (Lab2 area/tags UI polish, no automated tests, chat loading indicator, port-8000 collision, .env.pgvector mismatch, Gemini 429 risk)."
supersedes: rag-ai-local/functionality-docs/09022026/02_handoff-reranking-and-ui-toggle.md
tags: [rag-pipeline, reranking, metadata-filtering, cross-encoder, status, area, handoff]
keywords: [status=current, area scoping, include_reference, rerank-service, distractor documents]
related: [rag-ai-local/functionality-docs/09022026/01_reranking-service-and-toggle.md, rag-ai-local/functionality-docs/09022026/03_metadata-filtering-problems-and-tradeoffs.md, rag-ai-local/QandA/09022026_Reranker_Fooled_By_Distractor_Documents.md, rag-ai-local/QandA/09022026_Docker_Restart_Does_Not_Load_New_Env_Vars.md]
---

## TL;DR
- **What:** Finished and verified both cross-encoder reranking (`rerank-service`) and the metadata-filtering fix (`status`/`area`) it turned out to need — the reranker alone was found to make answers *worse* on adversarial content, and the fix for that had its own regression, also now fixed.
- **Why:** The user asked to add reranking for retrieval quality; using it immediately surfaced a real accuracy bug, which led to designing and implementing document-level authoritative-source tagging.
- **Where:** `session4-rag/rerank-service/` (new container); `rag_pipeline/config/`, `indexing/`, `retrieval/`, `api/`, `ui/index.html`.
- **Impact:** Both the originally-reported bug (wrong PTO-days answer) and a regression introduced mid-fix (a different, previously-correct question broke) are fixed and verified together.

## Current Status

Everything below has been executed against the live stack and its output observed — none of it is untested code:
- `rerank-service` running, model verified correct in isolation (`+6.2` relevant vs. `-11` irrelevant test scores).
- `/chat` reranking toggle (`rerank: true|false`, `RERANK_ENABLED` env default) verified both ways, `"reranked"` field in response confirmed accurate.
- `retrieval_scores.before_rerank`/`after_rerank` (with full content, `status`, `area` per candidate) and `metadata_filter` (`excluded_count`, `restricted_to_current`) confirmed present and correct in the API response; UI right-side debug panel renders them.
- 7-document PTO eval corpus: `02_correct_leave_policy.md` tagged `status=current, area=leave-entitlement`; `06_request_process_distractor.md` tagged `status=current, area=leave-request-process`; the other 5 (distractors + archived) remain untagged/excluded by default.
- Both previously-failing questions now answer correctly; the `include_reference` override confirmed to restore the original (buggy) unfiltered behavior on demand.

## COMPLETED

- **Reranking end-to-end** (was blocked in the previous handoff) — fixed via `docker compose down && docker compose up -d` (full stack recreation, needed to inject `RERANK_HOST`/`RERANK_HOST_PORT`/`RERANK_ENABLED` into `rag-app`'s environment). Confirmed via `docker exec rag-app printenv | grep -i rerank` showing all three vars, then live `/chat` calls both ways.
- **Retrieval debug panel** — `retrieval_scores` API field + `ui/index.html` right-side panel showing before/after candidate pools (full content, scores, status/area badges) and a "References by Document" summary. Built specifically so reranking's effect (and later, the metadata filter's effect) could be inspected directly instead of guessed at.
- **Root-caused a real reranking accuracy bug** using that same debug panel — see `03_metadata-filtering-problems-and-tradeoffs.md` and `09022026_Reranker_Fooled_By_Distractor_Documents.md` for the full trace: the cross-encoder loses to keyword-stuffed decoys that quote the question while disclaiming an answer.
- **Metadata filtering implemented** (Lab2, previously stubbed): `indexing/step5_metadata_extraction.py` (real YAML frontmatter parsing) + `POST /upload`'s optional `status`/`area` form fields (since this test corpus has no frontmatter at all) + `retrieval/step5_metadata_filter.py` (area-scoped `status=current` preference, `include_reference` override).
- **Caught and fixed a self-introduced regression** before declaring this done — the first (area-blind) version of the filter fixed the reported bug but broke a different, previously-correct question. Diagnosed with the same debug panel, fixed by scoping the filter to `area`, and both questions now verified working together.

## NOT DONE / STILL OPEN

- **Scaling the tagging workflow:** only 2 of 7 documents in the current corpus are tagged. Any topic without an explicitly-tagged `status=current` document gets zero protection from the reranker's decoy-susceptibility (falls back to unfiltered retrieval, same as before this fix). This is a real, accepted trade-off (see `03_metadata-filtering-problems-and-tradeoffs.md`), not a bug — but it means the fix only helps topics someone has curated.
- **`indexing/step5_metadata_extraction.py`** only extracts `status`/`area` in practice so far (nothing yet uses `tags`/`title`/`date`/`summary` from frontmatter, though `extract_metadata_martin` returns the whole parsed dict).
- All prior-session "NOT DONE" items remain untouched: local-`py main.py`-vs-`rag-app` port-8000 collision, `.env.pgvector` vs. live-container credential mismatch, no automated test suite, no chat-UI loading indicator (this matters less now that Gemini responses are fast, but still a real gap), Gemini free-tier `429` risk under sustained real usage.
- No UI affordance yet for *viewing* which documents are already tagged `status`/`area` before uploading a new one (would help avoid picking a colliding or redundant area name) — currently the only way to check is `psql` or the debug panel after asking a relevant question.

## NEXT ACTION

If the corpus grows, tag each new topic's authoritative document with `status=current` + a distinct `area` at upload time (via the UI's status/area fields) to get the same protection demonstrated here. Otherwise, pick up any of the older open items listed above — none are blocking.

To resume and re-verify current state:
```
curl -s -X POST http://localhost:8000/chat -H "Content-Type: application/json" \
  -d '{"question": "How many PTO days does a full-time employee receive per year?"}'
# expect: 18 days, sources include 02_correct_leave_policy.md, metadata_filter.restricted_to_current: true

curl -s -X POST http://localhost:8000/chat -H "Content-Type: application/json" \
  -d '{"question": "How do I submit a PTO request?"}'
# expect: correct step-by-step answer, sources include 06_request_process_distractor.md
```

## CONTEXT THE NEXT SESSION CANNOT DERIVE FROM CODE

- **Decision:** `status=current` is a positive/authoritative marker, not an exclusion list of "bad" statuses (`archived`, `distractor`, etc.). **Reason:** the actual bug involved 4 documents that weren't archived at all — enumerating every kind of "bad" content is a losing game; marking what's *right* sidesteps needing to know what's wrong with each decoy. **Rejected alternative:** a `status=archived` exclusion filter, which was checked against the real data before implementing and found insufficient (see Q2 in the QandA doc).
- **Decision:** the `status=current` restriction is scoped by `area`, not applied globally. **Reason:** a global version was implemented first and immediately broke a second, unrelated question in testing (`02_correct_leave_policy.md`'s embedding is broadly PTO-similar, not just "how many days"-similar) — this was caught by deliberately testing a second question after the first fix, not assumed to be fine.
- **Trap:** re-uploading a document's content (extracted from Postgres to re-tag it) via `curl -F "file=@/tmp/some-temp-name.md"` creates a **new** row instead of updating the existing one, because the upsert key (`source_path`) is derived from the uploaded filename, and curl names the upload after the local temp file's path — not the original document's name. Always rename the local file to match the original before re-uploading, and verify the row count in `rag_documents` afterward.
- **Trap:** curl's `-F "file=@path;filename=other-name.md"` syntax (the "obvious" fix for the above) returned exit code 26 in this environment — renaming the local file first was the working alternative.
- **Ground truth:** the cross-encoder reranker itself (`ms-marco-MiniLM-L-6-v2`) is not broken or misconfigured — it's functioning exactly as such models do, and the specific test corpus here was evidently built to probe for exactly this weakness. Don't mistake future decoy-content failures for a reranker bug; they're an inherent property of relevance-only scoring, addressed at the metadata layer, not by tuning the reranker.
