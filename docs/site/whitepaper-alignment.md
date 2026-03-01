# White Paper Alignment

This page maps FP runtime implementation to the white paper goals.

## Goal-to-implementation matrix

| White paper goal | Runtime realization | Verification |
| --- | --- | --- |
| Graph-first collaboration substrate | `fp.graph` entity/organization/membership relations + session/activity/event model | Integration scenarios in `tests/integration/test_section3_scenarios.py` |
| Multi-party by default | Session participants + role map + policy/budget metadata | Conformance + Section 3.1/3.2/3.5 tests |
| Evidence-first governance | Policy hooks create provenance records for allow/deny decisions | Policy-driven tests and audit bundle checks |
| Verifiable value exchange | Meter -> Receipt -> Settlement -> Dispute primitives | Section 3.3/3.4 tests + economy examples |
| Progressive disclosure and token efficiency | Ref-friendly payload paths, event streaming, token/cost meters | Token meter tests + example flows |
| Interoperable control plane semantics | Canonical models + OpenRPC + JSON-RPC dispatcher | `spec/` validation + transport unit tests |

## Section 3 scenario coverage

- **3.1 Daily work orchestration**: tool/resource/ui collaboration
- **3.2 Organization governance**: role-bearing members and high-risk policy gate
- **3.3 Procurement/service relationship**: long-running work + receipt + settlement
- **3.4 Market allocation**: bid/allocate event ordering + economic attestation
- **3.5 Social governance**: dispute/revocation and audit export

## What this runtime intentionally does not lock down

- No mandatory DID method
- No mandatory payment rail
- No mandatory scheduler/orchestrator
- No single transport requirement

This keeps FP as a stable control-plane protocol while preserving deployment freedom.
