# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

> See [.claude/rules/file-organization.md](.claude/rules/file-organization.md) for the full, authoritative file-organization rules.

## What this repository is

There is no application code here yet. The repository currently contains only a
Claude Code configuration scaffold (`.claude/`) that defines a **RAG-ready knowledge
base filing system** — rules and skills for where documentation must be created and
what metadata it must carry, so that everything written here can later be chunked,
embedded, and retrieved. There are no build, lint, or test commands because there is
no source code to build.

If application code is added later under this root, re-run `/init` (or update this
file) to add real build/lint/test commands and architecture notes for it.

## Current on-disk state (important — some referenced paths don't exist yet)

- `.claude/rules/file-organization.md` — the authoritative rule set (see below).
- `.claude/skills/write-qanda-doc/SKILL.md`
- `.claude/skills/write-functionality-doc/SKILL.md`
- `.claude/skills/write-handoff-doc/SKILL.md`
- `.claude/skills/write-business-rule-doc/SKILL.md`

The rule file references a few paths that **do not exist in this repo yet**:
`must-read.md` (root), `rag-ai-local/QandA/`, `rag-ai-local/functionality-docs/`,
and `rag-ai-local/template/*.md` (including `_METADATA_SCHEMA.md`). The first time
any of these are needed, create them (folders on first use; `must-read.md` and the
templates only if/when the user asks for them) — do not assume they already exist.

## The filing system (from `.claude/rules/file-organization.md`)

Every knowledge Markdown file in this repo must live in exactly one of two places,
so the corpus stays RAG-ready:

- `rag-ai-local/QandA/MMDDYYYY_<Title_Case_Topic>.md` — one file per distinct
  question topic (a day can have several files); questions inside are numbered
  `Q1`, `Q2`, … **per file**, never a running global counter.
- `rag-ai-local/functionality-docs/MMDDYYYY/NN_<slug>.md` — everything else that
  is project knowledge (plans, design notes, investigations, post-mortems,
  handoffs, business-rule extractions). `NN` is a two-digit sequence number for
  creation order *that day* — list the date folder first and use
  `max(existing NN_) + 1`, zero-padded; there is **no feature-named subfolder**,
  only date folders. The feature/area goes in the `area:` frontmatter field instead.

**Do not create any other knowledge `.md` file** (not at the repo root, not in an
arbitrary folder). The only `.md` files allowed outside `rag-ai-local/` are: rule
files (`must-read.md`, `.claude/rules/*.md`), skill files (`.claude/skills/**/SKILL.md`),
init/project docs (`CLAUDE.md`, `README.md`, `REQUIREMENT.MD` at root), and
code-adjacent/auto-generated `.md` that lives with actual code or tooling once
that exists.

Every file under `rag-ai-local/` must start with YAML frontmatter as its literal
first line (never after an H1), followed by a `## TL;DR` (What/Why/Where/Impact).
QandA and functionality docs share the identical frontmatter core
(`title`, `date`, `type`, `area`, `status`, `session_id`, `tags`, `related`); only
`type` differs (`qanda` vs `functionality`). `tags` are a small controlled set of
filter facets; `keywords` (when present) are literal identifiers for full-text
search (error codes, function names) — don't conflate the two.

Date handling: resolve `currentDate` once per session into `MMDDYYYY` (zero-padded,
no separators) and reuse that same string for every file/folder created in the
session. Never guess the date if it's missing from context — ask.

## Rule vs. Skill split

The rule file only defines the *constraint* (where files go, what metadata is
required). The *procedure* for actually producing each document type is a skill,
loaded only when that task is happening:

| Task | Skill |
|------|-------|
| Write a Q&A doc | `.claude/skills/write-qanda-doc` |
| Write a functionality/design/post-mortem doc | `.claude/skills/write-functionality-doc` |
| Write a session handoff | `.claude/skills/write-handoff-doc` |
| Extract business rules from code | `.claude/skills/write-business-rule-doc` |

Notable behaviors specific to each skill:

- **write-qanda-doc**: questions must be specific and searchable (real technology
  names, component names, concrete error codes) — a generic question like "why did
  this happen?" matches every doc in the corpus and pollutes retrieval. Answers lead
  with the conclusion, then an evidence block, then root cause and the `file:line` fix.
- **write-business-rule-doc**: every extracted rule (`BR-NNN`) must be tagged
  `CONFIRMED`, `INFERRED`, or `SUSPECT`, and must record the source commit
  (`git rev-parse --short HEAD`) since the doc is unverifiable without it. `SUSPECT`
  (behavior that looks like a bug, not an intended rule) must never be silently
  normalized into something that sounds intentional.
- **write-handoff-doc**: run *before* compacting/clearing context, not after — the
  whole point is to preserve details that would otherwise be lost. The one
  irreplaceable section is "CONTEXT THE NEXT SESSION CANNOT DERIVE FROM CODE"
  (decisions + reasons, rejected alternatives, traps already hit); everything else
  is re-derivable from the repo. A new handoff sets `supersedes:` on the old one and
  flips the old file's `status` to `superseded` rather than deleting it.

## Sync note

`file-organization.md` states that Rules 6, 8, and 9 are duplicated in a root
`must-read.md` file and must be kept in sync if either changes. That file does not
exist in the repo yet — if it's created later, keep the two in sync as instructed.
