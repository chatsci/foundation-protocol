# Architecture

## Layered design

```text
quickstart -> app -> runtime -> protocol/models -> stores/adapters/transport
```

Cross-cutting modules:

- `policy`: policy hooks and decision recording
- `observability`: metrics/trace/token-cost/audit export
- `economy`: meter/receipt/settlement/dispute primitives
- `security`: auth/authz/signature helpers
- `registry` + `profiles`: schema/event/profile extension points

## Package map

- `fp.quickstart`: one-screen integration APIs for common entity types
- `fp.app`: server/client composition surface
- `fp.runtime`: activity/session/event/dispatch/idempotency engines
- `fp.protocol`: canonical objects, enums, methods, and error model
- `fp.graph`: entity/organization/membership/relationship semantics
- `fp.stores`: abstract contracts + in-memory / sqlite / redis stubs
- `fp.adapters`: framework integration boundary (L0 contract)
- `fp.transport`: protocol transport adapters (inproc/stdio/http/sse/ws)
- `fp.transport.http_jsonrpc.JSONRPCDispatcher`: JSON-RPC 2.0 method dispatch layer

## Reliability semantics

- Activity transitions are validated by a canonical state machine.
- Activity start requires active session and participant-consistent owner/initiator.
- Idempotency keys are fingerprinted; conflicting payload reuse is rejected.
- Event streams support replay + resubscribe + ack.
- Backpressure enforces bounded unacked delivery windows.
- Policy decisions are persisted as provenance records.

## Token efficiency and latency design

- Progressive disclosure: send refs and compact payloads first.
- Structured events: avoid re-sending large context blocks.
- Delta-friendly updates: push only changed fields when possible.
- Metering hooks: measure token usage and cost per activity path.
