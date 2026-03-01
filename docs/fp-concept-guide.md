# FP Concept Guide

An intuitive walkthrough of what FP does, why it matters, and how to use it in practice.

## Episode 1: The Old World (ad-hoc integrations)

```text
+--------------------------------------------------------------+
| Scene: AI City, 2:00 AM                                      |
|                                                              |
| Planner Agent: "Where is Tool Weather?"                     |
| Tool Weather:  "Who are you? Why should I answer?"          |
| UI Console:     "I got 3 different payload formats..."      |
| Finance Bot:    "Who pays for this call? No receipt found." |
| Ops:            "We only have logs, no protocol evidence."  |
+--------------------------------------------------------------+
```

Without FP, collaboration often means bespoke glue:

- entity identity is implicit
- state transitions are ambiguous
- event replay and ack semantics are inconsistent
- governance and settlement are bolted on later

## Episode 2: FP Arrives (shared control plane)

```text
+-------------------------------------------------------------+
| Scene: Same city, next day                                  |
|                                                             |
| FP Runtime: "Everyone speaks the same contract now."       |
| Planner Agent: "I start a session with explicit roles."    |
| Tool Weather:  "I run as an owner entity in an activity."  |
| Policy Guard:  "High-risk operations require approval."    |
| Finance Bot:   "Meter -> Receipt -> Settlement is ready."  |
+-------------------------------------------------------------+
```

FP standardizes the collaboration loop:

1. register entities
2. create a governed session
3. start activity with explicit owner/initiator
4. stream + ack events
5. produce usage/economic evidence

## Episode 3: Publish and be discovered

```text
Entity A                              Directory                       Entity B
---------                             ---------                       ---------
[FPServer A] -- publish card -------> [entity_id -> card] <----- resolve + connect -- [FPClient B]
       |                                                                      |
       +-- /.well-known/fp-server.json                                        +-- JSON-RPC call
```

This is how others find and collaborate with your FP runtime:

- you publish your `FPServerCard`
- directory resolves `entity_id -> rpc_url`
- remote entities call FP methods over JSON-RPC

## Episode 4: Minimal implementation (non-toy)

```python
from fp.app import FPServer, make_default_entity
from fp.protocol import EntityKind
from fp.transport import FPHTTPPublishedServer

server = FPServer(server_entity_id="fp:system:seller")
server.register_entity(make_default_entity("fp:agent:seller", EntityKind.AGENT))
server.register_entity(make_default_entity("fp:agent:buyer", EntityKind.AGENT))

server.register_operation("trade.quote", lambda p: {"asset": p["asset"], "price": 42.0})

session = server.sessions_create(
    participants={"fp:agent:seller", "fp:agent:buyer"},
    roles={"fp:agent:seller": {"provider"}, "fp:agent:buyer": {"consumer"}},
)

activity = server.activities_start(
    session_id=session.session_id,
    owner_entity_id="fp:agent:seller",
    initiator_entity_id="fp:agent:buyer",
    operation="trade.quote",
    input_payload={"asset": "GPU-HOUR"},
)

print(activity.state.value, activity.result_payload)

with FPHTTPPublishedServer(server, publish_entity_id="fp:agent:seller", host="127.0.0.1", port=0) as pub:
    print(pub.rpc_url)
```

## Episode 5: Token economy and latency discipline

```text
+------------------------------------------------------------------+
| FP Rulebook                                                      |
| 1) session budget enforces hard token limit                      |
| 2) oversized output uses compaction + result_ref                 |
| 3) event streams use replay/ack/backpressure to avoid overload   |
+------------------------------------------------------------------+
```

Why this matters:

- avoids context explosion
- keeps payloads transport-friendly
- lowers tail latency and inference cost

## Episode 6: Governance and trust

```text
+---------------------------------------------------------------+
| Policy Hook: PRE_INVOKE                                      |
| Decision: DENY / ALLOW                                       |
| Provenance: written with policy_ref + subject_refs + outcome |
+---------------------------------------------------------------+
```

The result is operational trust:

- every sensitive action has explicit decision evidence
- settlement/dispute workflows have protocol artifacts
- audit reconstruction is deterministic

## Quick map: who uses FP and how

- Agent teams: expose an FP runtime and register operations.
- Platform teams: run directory + policy presets + observability.
- Tool/service owners: publish their own FP server cards.
- Buyers/consumers: resolve entity ids and collaborate remotely.

## 5-minute path after this guide

1. run [Getting Started](getting-started.md)
2. run full scenarios from [Examples](examples.md)
3. inspect [Architecture](architecture.md)
4. validate runtime and deployment checks via [Operations](operations.md)
