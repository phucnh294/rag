# RAG Metadata Schema — Source of Truth

Canonical field list for every `.md` under `rag-ai-local/`. See
`.claude/rules/file-organization.md` (Rule D, Rule E) for the rules that point here.

## Core fields (every file, every type)

| Field | Required | Meaning |
|---|---|---|
| `title` | yes | Human title. Also full-text indexed. |
| `date` | yes | ISO `YYYY-MM-DD`. Time-range pre-filter. |
| `type` | yes | `qanda` \| `functionality` \| `business-rule` \| `session-handoff`. |
| `area` | yes | Feature/functionality slug. Facet pre-filter. |
| `status` | yes | `investigation` \| `in-progress` \| `implementation-complete` \| `superseded`. |
| `session_id` | yes | The session that produced the doc. |
| `duration` | no | How long the work took, e.g. `108min`. |
| `tags` | yes | Array. Small controlled vocabulary. **Facets you FILTER on.** |
| `keywords` | no | Array. Literal identifiers (`ERR-6002`, class/function names, error codes). **Terms you SEARCH for** — BM25's job, not the embedding's. |
| `related` | no | Filenames of sibling docs that actually exist. |

## Type-specific extra fields

- `qanda` → `issue_type`, `severity`, `resolution_date`.
- `functionality` → `files`, `version`, `last_updated`, `extraction_method`.
- `business-rule` → `source_code_version` (commit hash the rules were read from).
- `session-handoff` → `next_action`, `supersedes`.

## `tags` vs `keywords`

- `tags` = small controlled vocabulary you filter on (`crawler`, `auth`, `db`).
- `keywords` = exact strings a person will paste into search (`AtomicLong`,
  `CACHE_MIN_SIMILARITY`, `NoSuchElementException`). Embeddings are worst at
  exact identifiers; BM25/full-text is best at them — `keywords` feeds that path.

## Chunking contract

- Frontmatter is **line 1** of the file — no `# Heading` above it, or the YAML
  parser sees body text instead of metadata and the doc indexes with no filters.
- Each `##` heading is a retrieval chunk. Write every section so it stands alone
  without the sections above it — repeat the subject noun instead of "it".
- The `## TL;DR` block is a dense summary chunk; it must carry `What / Why /
  Where / Impact` so a single-chunk retrieval still answers the gist.
