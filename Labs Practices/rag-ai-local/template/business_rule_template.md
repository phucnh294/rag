---
title: <Human title — e.g. "Account Eligibility Rules">
date: <YYYY-MM-DD>
type: business-rule
area: <feature-slug>
status: <investigation|in-progress|implementation-complete|superseded>
session_id: <session id>
source_code_version: <git short hash the rules were extracted from>
tags: [tag1, tag2]
keywords: [ExactIdentifier]
related: []
---

## TL;DR
- **What:** one line — the system/module these rules govern.
- **Why:** why the rules were extracted (onboarding, audit, bug investigation).
- **Where:** the files/components read.
- **Impact:** number of rules found, and any `SUSPECT` rules flagged.

## BR-001: <Rule stated in business language, not code language>

**Trust:** `CONFIRMED` | `INFERRED` | `SUSPECT`

**Source:** `path/to/file.py:88`

**Evidence:**
```python
<minimal code snippet proving the rule>
```

**Edge cases observed:** <what happens at the boundary — nulls, empty, concurrent, etc.>

<!-- Repeat ## BR-002, ## BR-003, ... one block per rule. -->

## Rules index

| ID | Rule (short) | Trust | Source |
|---|---|---|---|
| BR-001 | <short description> | CONFIRMED/INFERRED/SUSPECT | `file.py:88` |
