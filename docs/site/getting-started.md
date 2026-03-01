# Getting Started

This guide takes you from zero setup to a runnable FP integration.

By the end, you will be able to:

- create a multi-entity FP session
- execute activities through registered operations
- stream and ack events safely
- add policy control for high-risk actions
- expose runtime methods through JSON-RPC

## 0) Prerequisites

- Python `>=3.10`
- repository checked out locally

Install runtime:

```bash
python3 -m pip install -e .
```

Install development + docs extras:

```bash
python3 -m pip install -e ".[dev,docs]"
```

## 1) Run a known-good example first

Before writing your own code, run the baseline example:

```bash
PYTHONPATH=src python3 -m examples.quickstart.basic_flow
```

Expected output shape:

- first line: `completed`
- second line: result payload containing `city` and `temp_c`

This validates your local environment and FP import path.

## 2) Build your first FP workflow (minimal but real)

Create `demo_fp.py` and run it.

```python
from fp.app import FPServer, make_default_entity
from fp.protocol import EntityKind

server = FPServer(server_entity_id="fp:system:runtime")

# 1) Register participants
server.register_entity(make_default_entity("fp:agent:planner", EntityKind.AGENT))
server.register_entity(make_default_entity("fp:tool:weather", EntityKind.TOOL))

# 2) Create governed collaboration context
session = server.sessions_create(
    participants={"fp:agent:planner", "fp:tool:weather"},
    roles={
        "fp:agent:planner": {"coordinator"},
        "fp:tool:weather": {"provider"},
    },
    policy_ref="policy:trip-planning",
)

# 3) Register an operation implementation
server.register_operation(
    "weather.lookup",
    lambda payload: {"city": payload["city"], "forecast": "sunny", "temp_c": 23},
)

# 4) Start activity (idempotency key recommended in production)
activity = server.activities_start(
    session_id=session.session_id,
    owner_entity_id="fp:tool:weather",
    initiator_entity_id="fp:agent:planner",
    operation="weather.lookup",
    input_payload={"city": "San Francisco"},
    idempotency_key="idem-weather-demo-1",
)

# 5) Read result
result = server.activities_result(activity_id=activity.activity_id)
print(activity.state.value)
print(result["result"])

# 6) Consume events
stream = server.events_stream(session_id=session.session_id)
events = server.events_read(stream_id=stream["stream_id"], limit=100)
print(f"events={len(events)}")
server.events_ack(stream_id=stream["stream_id"], event_ids=[e.event_id for e in events])
```

Run:

```bash
PYTHONPATH=src python3 demo_fp.py
```

## 3) Add governance (high-risk approval)

Use policy engine hooks to enforce organizational controls.

FP supports pre-invoke, pre-role-change, and pre-settlement checks.

Runnable reference:

```bash
PYTHONPATH=src python3 -m examples.scenarios.governed_transfer
```

What this demonstrates:

- denied path when required approval metadata is missing
- allowed path when approval evidence is present
- policy decisions captured as provenance records

## 4) Add economy accountability

If your workflow has billable work or settlement semantics, attach economy artifacts.

Runnable reference:

```bash
PYTHONPATH=src python3 -m examples.scenarios.economy_settlement
```

What this demonstrates:

- meter record creation
- receipt issuance + integrity verification
- settlement confirmation

## 5) Add JSON-RPC transport integration

For service-facing integration, use `JSONRPCDispatcher`.

```python
from fp.app import FPServer
from fp.transport import JSONRPCDispatcher

server = FPServer()
dispatcher = JSONRPCDispatcher.from_server(server)

resp = dispatcher.handle(
    {
        "jsonrpc": "2.0",
        "id": "1",
        "method": "fp/ping",
        "params": {},
    }
)
print(resp)
```

Runnable reference:

```bash
PYTHONPATH=src python3 -m examples.scenarios.transport_jsonrpc
```

## 6) Run all provided scenarios

```bash
bash scripts/run_examples.sh
```

This executes:

- quickstart baseline
- LLM + tool collaboration
- governed transfer
- economy settlement
- JSON-RPC dispatch path

## 7) Validate release-grade quality

Run the project quality gate:

```bash
bash scripts/quality_gate.sh
```

This command covers:

1. full test suite
2. runnable examples
3. compile checks
4. spec validation

## Common pitfalls and fixes

### `FP_NOT_FOUND` for entities

Cause: session/activity references an entity that was never registered.

Fix: call `server.register_entity(...)` for every participant before session creation.

### `FP_AUTHZ_DENIED` on activity start

Cause: owner or initiator is not part of session participants.

Fix: include both in `participants` when creating/updating session.

### backpressure errors on event streams

Cause: reading too fast without acking.

Fix: ack consumed events regularly via `events_ack`.

### docs build fails locally (`No module named mkdocs`)

Cause: docs dependencies not installed in local Python environment.

Fix: install `.[docs]` extras or rely on CI docs workflow.

## Next steps

1. Review [Architecture](architecture.md) for component boundaries.
2. Review [White Paper Alignment](whitepaper-alignment.md) to verify design intent mapping.
3. Review [Examples](examples.md) for scenario-level integration templates.
4. Review [API Reference](api.md) for full callable surface.
