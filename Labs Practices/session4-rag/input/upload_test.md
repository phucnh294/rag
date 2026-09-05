---
title: Upload Test Doc
date: 2026-08-26
---

# Upload Test

This is a small test document used to verify that the /upload endpoint
correctly saves the file, chunks it, generates embeddings, and stores
everything in Postgres.

It only needs a handful of sentences to produce at least one chunk once
tokenized, so this paragraph exists purely to pad out the token count a
little further for a realistic end-to-end check.
