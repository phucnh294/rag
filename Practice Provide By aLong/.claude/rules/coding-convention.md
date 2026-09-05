# Coding Convention

## Rule 1 — Every Python function must have complete type hints

Every Python function/method defined in this repo (excluding test files matched by
`test_*.py` / `*_test.py`) must annotate **all parameters** and the **return type**.

❌ Rejected:
```python
def add(a, b):
    return a + b
```

✅ Accepted:
```python
def add(a: int, b: int) -> int:
    return a + b
```

**Why:** untyped signatures are the single biggest source of silent argument-order
and wrong-type bugs in a codebase with no compiler — type hints turn that class of
bug into a static, checkable error instead of a runtime surprise.

**How to verify (must pass with zero errors before a change is considered done):**

```bash
python -m mypy --disallow-untyped-defs .
```

- Exit code `0` and no `error:` lines in the output = compliant.
- Any `error: Function is missing a type annotation` = violation — fix the
  signature, don't suppress with `# type: ignore`.

**Scope note:** this rule applies once Python source files exist in the repo. There
is no Python source under version control yet (see root `CLAUDE.md`), so there is
nothing to lint today — this rule takes effect the first time a `.py` file is added.
