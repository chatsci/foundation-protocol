# Release Readiness

Use this checklist before tagging a release intended to accompany the white paper.

## Functional readiness

- Core runtime tests pass (unit + conformance + integration + perf smoke)
- Section 3 scenario tests pass
- Example smoke tests pass
- Spec artifacts validate against OpenRPC/JSON Schema checks

## Engineering readiness

- No TODO/FIXME placeholders in production paths
- Deterministic schema hashing and stable idempotency semantics
- Session/activity/event invariants enforced with explicit errors
- JSON-RPC transport path validates request shape and error mapping

## Documentation readiness

- README contains onboarding, architecture, and operations guidance
- MkDocs site includes architecture, examples, operations, and API references
- White-paper alignment matrix is up to date
- Example commands are executable

## Required commands

```bash
bash scripts/quality_gate.sh
bash scripts/build_docs.sh
```

## CI gates

- `ci.yml`: quality gate (tests/spec/examples/compile)
- `docs.yml`: MkDocs build + GitHub Pages deploy
