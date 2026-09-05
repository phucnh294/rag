# CLAUDE.md

This file provides guidance to Claude Code when working in this repository.

## Coding Standards

This is a Python project. All Python code written or modified in this repository **must** follow the conventions defined in [.claude/rules/python-coding-standards.md](.claude/rules/python-coding-standards.md) — formatting, naming, type hints, docstrings, project structure, error handling, testing, dependencies, and logging.

These rules are mandatory, not optional guidance. Before writing or editing Python code, apply them; when reviewing code, check against them.

## File Organization

All knowledge/documentation `.md` files **must** follow [.claude/rules/file-organization.md](.claude/rules/file-organization.md) — every knowledge doc lives under `rag-ai-local/` (either `QandA/` or `functionality-docs/`), with `MMDDYYYY`-based naming and mandatory frontmatter + TL;DR. Do not create knowledge `.md` files at the repo root or in any other folder.

This rule is mandatory, not optional guidance.

## Skills

Use these skills for their matching task instead of writing docs ad hoc:

| Task | Skill |
|------|-------|
| Build the Docker image and verify it prints "Hello" | [.claude/skills/run-hello](.claude/skills/run-hello/SKILL.md) |
| Write a Q&A doc | [.claude/skills/write-qanda-doc](.claude/skills/write-qanda-doc/SKILL.md) |
| Write a functionality / design / post-mortem doc | [.claude/skills/write-functionality-doc](.claude/skills/write-functionality-doc/SKILL.md) |
| Write a session handoff | [.claude/skills/write-handoff-doc](.claude/skills/write-handoff-doc/SKILL.md) |
| Extract business rules from code | [.claude/skills/write-business-rule-doc](.claude/skills/write-business-rule-doc/SKILL.md) |
