---
title: Structure-Aware Chunking (Markdown Headings/Paragraphs, Not Fixed Tokens)
date: 2026-09-05
type: functionality
area: rag-pipeline-indexing
status: implementation-complete
session_id: n/a
duration: ~45min
files: [Labs Practices/session4-rag/rag_pipeline/indexing/step3_chunking_strategy.py]
version: 1
last_updated: 2026-09-05
extraction_method: pair-session
tags: [rag-pipeline, chunking, indexing, markdown, tokenization]
keywords: [chunk_body_martin, tiktoken, CHUNK_SIZE_TOKENS, cl100k_base, sliding-window]
related: [rag-ai-local/functionality-docs/09052026/03_hybrid-search-rrf.md, rag-ai-local/functionality-docs/09052026/01_handoff-chunking-and-hybrid-search.md]
---

## TL;DR
- **What:** Replaced `indexing/step3_chunking_strategy.py`'s blind fixed-token sliding-window chunking with structure-aware chunking that splits on markdown headings/paragraphs first.
- **Why:** Fixed-token chunking cuts wherever the Nth token happens to fall — including mid-sentence or between a heading and the paragraph it introduces — hurting both embedding quality and reranker precision.
- **Where:** `indexing/step3_chunking_strategy.py` (full rewrite, same public signature).
- **Impact:** Verified locally (3 unit-test scenarios) and live against the 7-doc PTO corpus (re-indexed via upsert, no duplicates, tags preserved, both prior regression questions still answer correctly).

## What it does

`chunk_body_martin(body_text: str) -> list[str]` still returns a flat list of chunk strings — same signature as before — but now builds them by walking the document's own markdown structure instead of a raw token count. A chunk boundary can only fall between paragraphs (or between sections), never in the middle of a sentence, and never between a heading and the content it introduces.

## How it works

1. **Block splitting** (`_split_into_blocks_martin`): the body is split on blank lines into blocks. A block that is *only* a bare heading (nothing else on its own paragraph) is merged into the block that follows it — so `## Leave Entitlement` is never separated from the paragraph right after it.
2. **Greedy packing** (`chunk_body_martin`): blocks are appended to the current chunk, accumulating a running `tiktoken` count, until the next block would push the chunk over `CHUNK_SIZE_TOKENS` (800). At that point the chunk is flushed and a new one starts.
3. **Paragraph overlap**: instead of the old raw-token overlap, the last `_CHUNK_OVERLAP_PARAGRAPHS` (1) block(s) of the just-flushed chunk are carried forward as the start of the next chunk — bridging context across the boundary without ever re-cutting a sentence.
4. **Heading-context carry-forward**: if a new chunk doesn't start under its own heading (because it opened with an overlap-carried paragraph from mid-section), the most recently seen heading line is prefixed onto the chunk, so every chunk still carries the section title it belongs to.
5. **Oversized-block fallback** (`_split_oversized_block_martin`): if a single block (e.g. a huge table or code block with no internal blank lines) alone exceeds `CHUNK_SIZE_TOKENS`, it falls back to the *original* token-sliding-window logic just for that one block — bounding worst-case chunk size without adding complexity to the common case.

## Key decisions and why

- **Structure-aware over sentence-boundary-only chunking.** Sentence-boundary splitting alone (e.g. via a sentence tokenizer) avoids mid-sentence cuts but still lets a chunk span two unrelated headings. Structure-aware splitting fixes both problems for one implementation cost, using only `re` + `tiktoken` — no new dependency.
- **Structure-aware over semantic (embedding-based) chunking.** Semantic chunking (cut where adjacent-sentence embedding similarity drops) gives the best topical coherence per chunk, but requires an extra embedding pass at index time and a similarity threshold with no obvious default for this corpus. Rejected as overkill for the actual problem (mid-sentence/mid-heading cuts), not because it's a worse idea in general.
- **Paragraph-level overlap over the old fixed-token overlap.** The prior 120-token overlap could still land mid-sentence on either side of the boundary. Carrying forward whole blocks guarantees the overlap itself is coherent text, not a token-count coincidence.
- **Fallback preserved, not replaced.** Rather than inventing new logic for the oversized-single-block edge case, the exact prior token-sliding-window function was kept and reused only for that path — minimizes new surface area for a case that's rare by construction (a single un-blank-line-broken block bigger than 800 tokens).

## Configuration

- `CHUNK_SIZE_TOKENS = 800` — unchanged from before this rewrite; the target size a chunk is packed up to (chunks can end up smaller if the next block would overflow it — this is intentional, a slightly small coherent chunk beats a padded incoherent one).
- `CHUNK_OVERLAP_TOKENS = 120` — now used ONLY by the oversized-block fallback path, not by normal packing (which uses `_CHUNK_OVERLAP_PARAGRAPHS` instead).
- `_CHUNK_OVERLAP_PARAGRAPHS = 1` — new constant; how many trailing blocks of a chunk carry forward into the next one.

## Gotchas

- **A chunk's actual token count can be noticeably below 800** even when there's more content left to pack — this happens whenever the *next* block alone would overflow the budget, and is correct behavior, not a bug: the alternative (splitting that next block to fit) would reintroduce the exact mid-sentence-cut problem this rewrite exists to fix.
- **Re-indexing existing documents is required** to get them rechunked under the new logic — the upsert (`ON CONFLICT (source_path) DO UPDATE`) only rechunks a document when it's re-uploaded; documents indexed under the old code keep their old chunk boundaries until then.
- **With this project's current 7-doc test corpus, every document is short enough to fit in a single chunk** — the multi-chunk packing/overlap/heading-prefix logic has been verified in local unit tests (see Verification) but not yet exercised end-to-end through the live pipeline against a document long enough to actually split. This is a real verification gap, not a defect.

## Verification

Local unit tests (`rag_pipeline/`, run via `python -c "..."` importing `chunk_body_martin` directly):
```
1. Small doc (2 headings, ~80 tokens): 1 chunk, both headings/paragraphs intact.
2. Large doc (1 heading + 40 filler paragraphs, forcing a split):
   2 chunks — chunk 0 = 781 tokens, chunk 1 = 502 tokens.
   Paragraph 24 confirmed present at the END of chunk 0 AND the START of
   chunk 1 (the overlap), chunk 1 correctly prefixed with the heading line.
3. Oversized single block (~2000 tokens, no blank lines): 3 chunks via the
   fallback path, sizes 800/800/644 — bounded correctly.
```

Live, against the 7-doc PTO corpus:
```bash
# Re-upload each doc (upsert on source_path)
curl -F "file=@02_correct_leave_policy.md" -F "status=current" -F "area=leave-entitlement" http://localhost:8000/upload
# ... (all 7 docs)

# Confirm no duplicates, tags intact
docker exec pgvector psql -U ai_user -d ai_db -c "SELECT source_path, status, area FROM rag_documents ORDER BY source_path;"
# -> still exactly 7 rows, status/area unchanged

# Regression: both previously-fixed questions still correct
curl -X POST http://localhost:8000/chat -d '{"question": "How many PTO days does a full-time employee receive per year?"}'
curl -X POST http://localhost:8000/chat -d '{"question": "How do I submit a PTO request?"}'
# -> both answer correctly, same sources as before this change
```
