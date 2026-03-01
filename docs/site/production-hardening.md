# Production Hardening

This page summarizes the hardening layer added on top of the FP reference runtime so teams can evaluate production readiness quickly.

## What was hardened

### Runtime invariants

- strict session state-transition validation (`ACTIVE/PAUSED/CLOSING/CLOSED/FAILED`)
- role patch validation rejects empty role sets
- push config schema validation with required fields and URL constraints
- stream backpressure windows isolated per stream
- native async activity dispatch path for in-process async runtimes (no thread-bridge in core async engines)

### Integrity and safety

- receipt signatures bind full context (`receipt_id`, `activity_id`, `provider_entity_id`, `meter_records`)
- in-memory stores use defensive deep copies on `put/get/list`
- transport mapping uses stricter parameter checks for required method fields

### Federated collaboration

- entity-owned FP server publication via HTTP JSON-RPC
- well-known server card endpoint (`/.well-known/fp-server.json`)
- directory-based discovery and entity->server resolution
- remote FP client with structured FP error mapping
- transport-level retry/backoff/jitter and circuit-breaker controls
- HTTP keep-alive connection reuse for lower request overhead

### Data and API hardening

- `FPClient` is transport-only (single invocation path)
- SQLite store serialization uses JSON codec (no pickle)
- shared HTTP transport reused by federation remote client (no duplicate logic)
- list APIs support deterministic cursor pagination (`limit` + `cursor`)
- activities are indexed by `session_id` for scalable session-scoped listing
- activity start path extracted to dedicated orchestrator with step-level tests

### Spec integrity pipeline

- deterministic schema-sync manifest generated from `spec/fp-core.schema.json` and `spec/fp-openrpc.json`
- CI fails on schema/model artifact drift
- local commands:
  - `python scripts/generate_models_from_spec.py`
  - `python scripts/check_spec_sync.py`

## Non-toy scenario coverage

Integration suites now include:

- high-volume multi-entity orchestration (50+ activities in one governed session)
- long-running service workflow with replay/resubscribe/ack and economy closeout
- governed market allocation with deny/approve policy transitions, settlement, and disputes
- framework embedding pattern with shared runtime and quickstart entities
- federated publish/discover/connect/collaborate flow over HTTP

See:

- `tests/integration/test_section3_non_toy_workloads.py`
- `tests/integration/test_federation_network.py`

## Operational checks

Recommended gates:

1. `bash scripts/run_tests.sh`
2. `bash scripts/run_examples.sh`
3. `bash scripts/quality_gate.sh`

These commands validate conformance, integration, performance smoke, runnable scenarios, compile checks, and spec validation.

## Current boundaries

FP remains an in-memory-first reference runtime by default. For deployment at larger scale:

- replace in-memory stores with durable backends
- wire real identity/authn/authz infrastructure
- externalize key management for signatures
- deploy directory as a durable, access-controlled service

The current architecture is intentionally small and explicit, so these upgrades can be introduced without semantic drift from the core protocol.
