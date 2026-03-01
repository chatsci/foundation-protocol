# Architecture

## ASCII code architecture

```text
foundation-protocol/
├── src/fp/
│   ├── quickstart/        # Fast embedding APIs (Agent/Tool/Service/Resource)
│   ├── app/               # FPServer / FPClient composition boundary
│   ├── protocol/          # Canonical models, enums, errors, method contracts
│   ├── graph/             # Entity / Organization / Membership semantics
│   ├── runtime/           # Session / Activity / Event / Dispatch / Idempotency engines
│   ├── economy/           # Meter -> Receipt -> Settlement -> Dispute
│   ├── policy/            # Policy hooks + decisions
│   ├── observability/     # Metrics / token-cost / trace / audit export
│   ├── stores/            # Store interfaces + memory/sqlite/redis bundles
│   ├── transport/         # inproc / stdio / sse / websocket / jsonrpc / http publish
│   ├── federation/        # Server-card directory, resolver, remote client
│   ├── adapters/          # Framework adapter contracts
│   ├── security/          # Signatures + auth/authz helpers
│   ├── profiles/          # Protocol profile presets
│   └── registry/          # Schema / event type / pattern registries
├── tests/
│   ├── unit/
│   ├── conformance/
│   ├── integration/
│   └── perf/
├── examples/
│   ├── quickstart/
│   └── scenarios/
└── docs/site/
```

```text
                 +---------------------------------------------+
                 |                 FPServer                    |
                 |---------------------------------------------|
                 | app.server API                              |
                 +-------------------------+-------------------+
                                           |
      +----------------------+-------------+--------------+--------------------+
      |                      |                            |                    |
      v                      v                            v                    v
+-----------+        +--------------+            +---------------+      +-------------+
| protocol  |<------>| runtime      |<---------->| stores        |      | transport   |
| models    |        | engines      |            | (memory/...)  |      | jsonrpc/... |
+-----+-----+        +------+-------+            +---------------+      +------+------+ 
      |                     |                                              |
      |                     +---------------------+------------------------+
      |                                           |
      v                                           v
+-------------+                            +--------------+
| policy      |---- provenance ----------->| observability|
| hooks       |                            | + audit      |
+------+------+                            +------+-------+
       |                                           |
       v                                           v
  +----+-------------------------------------------+----+
  |                  economy pipeline                    |
  |       meter -> receipt -> settlement -> dispute      |
  +------------------------------------------------------+
```

```text
Federated collaboration path

Entity A publishes FPServer
   |
   +--> /.well-known/fp-server.json  (FPServerCard)
   |
Directory/Resolver indexes by entity_id
   |
Entity B resolves target entity_id
   |
RemoteFPClient -> JSON-RPC -> target FPServer
   |
sessions / activities / events / receipts / settlements
```

## Layered design

```text
quickstart -> app -> runtime -> protocol/models -> stores/adapters/transport -> federation
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
- `fp.transport.http_publish.FPHTTPPublishedServer`: publish local FP runtime as HTTP endpoint + well-known server card
- `fp.federation`: server card model, publish directory, network resolver, and remote FP client

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

## Federated deployment model

- each entity can expose an independent FP runtime endpoint
- published server card enables global entity->endpoint resolution
- remote entities can collaborate via FP method calls without sharing process/runtime
- governance and economy semantics remain identical for local and remote paths
