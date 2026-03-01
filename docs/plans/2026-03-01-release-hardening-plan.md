# FP Release Hardening Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Raise FP Python runtime to white-paper publishable quality with stronger runtime safety, practical transport integration, richer examples, and complete docs.

**Architecture:** Keep the core small and explicit while hardening state invariants and adding thin integration layers. Prioritize runtime correctness and traceable evidence outputs over feature sprawl.

**Tech Stack:** Python 3.10+, stdlib unittest, MkDocs + mkdocstrings, GitHub Actions.

### Task 1: Runtime Invariant Hardening

**Files:**
- Modify: `src/fp/app/server.py`
- Test: `tests/conformance/test_core_conformance.py`

**Step 1:** Add failing tests for missing session/participant/receipt checks.
**Step 2:** Run targeted conformance tests and confirm failures.
**Step 3:** Implement strict precondition checks in session/activity/event/settlement paths.
**Step 4:** Re-run targeted tests and confirm pass.

### Task 2: JSON-RPC Practical Transport Layer

**Files:**
- Modify: `src/fp/transport/http_jsonrpc.py`
- Modify: `src/fp/transport/__init__.py`
- Create: `tests/unit/test_jsonrpc_transport.py`

**Step 1:** Write failing transport tests for ping, notifications, invalid request handling, and FP error mapping.
**Step 2:** Implement JSON-RPC dispatcher with method table and robust payload normalization.
**Step 3:** Validate with unit tests.

### Task 3: Scenario Examples and Smoke Coverage

**Files:**
- Modify: `examples/quickstart/basic_flow.py`
- Create: `examples/__init__.py`
- Create: `examples/quickstart/__init__.py`
- Create: `examples/scenarios/__init__.py`
- Create: `examples/scenarios/llm_tool_collaboration.py`
- Create: `examples/scenarios/governed_transfer.py`
- Create: `examples/scenarios/economy_settlement.py`
- Create: `examples/scenarios/transport_jsonrpc.py`
- Create: `tests/integration/test_examples_smoke.py`

**Step 1:** Write failing smoke tests that import and run scenario examples.
**Step 2:** Implement each example as executable `run_example()` functions.
**Step 3:** Run smoke tests to verify practical usability.

### Task 4: Publish-Ready Docs and README

**Files:**
- Modify: `README.md`
- Modify: `mkdocs.yml`
- Create: `docs/site/whitepaper-alignment.md`
- Create: `docs/site/examples.md`
- Create: `docs/site/release-readiness.md`
- Modify: `docs/site/operations.md`
- Modify: `docs/site/api.md`

**Step 1:** Expand docs around white-paper goal alignment, usage patterns, and release process.
**Step 2:** Add example catalog and runnable commands.
**Step 3:** Ensure nav and API docs expose new transport/runtime surfaces.

### Task 5: Quality Gates and CI

**Files:**
- Create: `scripts/run_examples.sh`
- Create: `scripts/quality_gate.sh`
- Modify: `scripts/run_tests.sh`
- Modify: `pyproject.toml`
- Create: `.github/workflows/ci.yml`

**Step 1:** Add deterministic local quality gate scripts.
**Step 2:** Add CI workflow for tests/spec/examples/compile checks.
**Step 3:** Run full local validation before completion.
