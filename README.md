# Foundation Protocol (FP) - Python Reference Runtime

FP is a graph-first control plane for multi-entity AI systems.

This repository provides a publish-ready Python reference runtime aligned to the FP white paper: multi-party collaboration, policy-native governance, evidence-first operations, and verifiable value exchange.

## Release-grade highlights

- Canonical runtime semantics for `Entity`, `Organization`, `Membership`, `Session`, `Activity`, and `Event`
- Strict lifecycle enforcement for sessions/activities with explicit semantic errors
- Policy hooks with provenance recording for allowed/denied decisions
- Meter -> Receipt -> Settlement -> Dispute economy primitives
- Replayable event streams with resubscribe, ack, and backpressure safety
- Fingerprinted idempotency protection for write retries
- Practical JSON-RPC 2.0 dispatcher for FP method integration
- Federated FP server publication/discovery + remote client connectivity
- Transport reliability with retry/backoff/circuit-breaker + HTTP keep-alive reuse
- Cursor pagination contracts across memory/sqlite stores and runtime listing APIs
- Schema-first sync artifacts (`spec -> generated manifest`) with CI drift gate
- Runnable scenario examples + smoke tests
- MkDocs + mkdocstrings documentation site with GitHub Pages deployment

## White paper alignment

FP runtime design maps directly to white-paper goals:

1. Graph-first collaboration substrate
2. Multi-party coordination by default
3. Evidence-first governance and auditability
4. Ledger-agnostic but verifiable economic exchange
5. Token-efficient control-plane messaging

See docs page: `docs/site/whitepaper-alignment.md`.

## Installation

Runtime only:

```bash
python3 -m pip install -e .
```

Development and docs:

```bash
python3 -m pip install -e ".[dev,docs]"
```

## Quick start

```python
from fp.app import FPServer, make_default_entity
from fp.protocol import EntityKind

server = FPServer(server_entity_id="fp:system:runtime")

server.register_entity(make_default_entity("fp:agent:planner", EntityKind.AGENT))
server.register_entity(make_default_entity("fp:tool:weather", EntityKind.TOOL))

session = server.sessions_create(
    participants={"fp:agent:planner", "fp:tool:weather"},
    roles={
        "fp:agent:planner": {"coordinator"},
        "fp:tool:weather": {"provider"},
    },
    policy_ref="policy:trip-planning",
)

server.register_operation(
    "weather.lookup",
    lambda payload: {"city": payload["city"], "temp_c": 23},
)

activity = server.activities_start(
    session_id=session.session_id,
    owner_entity_id="fp:tool:weather",
    initiator_entity_id="fp:agent:planner",
    operation="weather.lookup",
    input_payload={"city": "San Francisco"},
    idempotency_key="idem-weather-001",
)

print(activity.state.value)  # completed
```

## JSON-RPC integration (in-process)

```python
from fp.app import FPServer
from fp.transport import JSONRPCDispatcher

server = FPServer()
dispatcher = JSONRPCDispatcher.from_server(server)

response = dispatcher.handle(
    {
        "jsonrpc": "2.0",
        "id": "1",
        "method": "fp/ping",
        "params": {},
    }
)
print(response)
```

## Scenario examples

Run all examples:

```bash
bash scripts/run_examples.sh
```

Included scenarios:

- `examples/quickstart/basic_flow.py`
- `examples/scenarios/llm_tool_collaboration.py`
- `examples/scenarios/governed_transfer.py`
- `examples/scenarios/economy_settlement.py`
- `examples/scenarios/transport_jsonrpc.py`
- `examples/scenarios/federated_discovery_trade.py`

## Federated publish/discover/connect

FP now supports entity-owned runtime publication and network discovery:

- publish local runtime via `FPHTTPPublishedServer`
- expose server card at `/.well-known/fp-server.json`
- register/discover cards via `InMemoryDirectory` (or your own directory service)
- connect with `RemoteFPClient` and invoke FP methods remotely

Core modules:

- `src/fp/transport/http_publish.py`
- `src/fp/federation/network.py`

## Quality gates

Single command:

```bash
bash scripts/quality_gate.sh
```

The quality gate runs:

1. All tests (`unit`, `conformance`, `integration`, `perf smoke`)
2. Example smoke tests
3. Compile sanity checks
4. Spec validation (`spec/fp-core.schema.json`, `spec/fp-openrpc.json`)
5. Spec-sync drift check (`scripts/check_spec_sync.py`)

## A+ hardening checkpoints

- `FPClient` uses a single transport invocation path (no server bypass path)
- `AsyncFPServer` public APIs have explicit named signatures
- In-process async runtime path executes natively (core async engines and async server facade avoid thread-bridge execution)
- SQLite persistence uses JSON codec (no pickle serialization)
- `RemoteFPClient` composes shared HTTP JSON-RPC transport logic
- Paged listing semantics (`limit` + `cursor`) are available across runtime/store surfaces
- Activity start orchestration is decomposed into dedicated orchestration steps
- Remote transport has bounded retry/backoff/jitter/circuit-breaker
- HTTP client supports keep-alive connection reuse for lower latency

## Documentation

Local preview:

```bash
bash scripts/serve_docs.sh
```

Static build:

```bash
bash scripts/build_docs.sh
```

Docs source lives in `docs/site/` and API reference is generated from `src/`.

Published site (GitHub Pages):

- https://chatsci.github.io/foundation-protocol/

Comic-style introduction:

- https://chatsci.github.io/foundation-protocol/comic-guide/

## CI workflows

- `.github/workflows/ci.yml`: quality gate for push + pull request
- `.github/workflows/docs.yml`: docs build and GitHub Pages deployment

## Repository structure

```text
src/fp/
  quickstart/      # one-screen integration APIs
  app/             # server/client composition layer
  protocol/        # canonical FP objects, methods, errors
  graph/           # entity/org/membership/relationship model
  runtime/         # session/activity/event/dispatch/idempotency engines
  economy/         # meter/receipt/settlement/dispute
  adapters/        # framework integration contract
  transport/       # inproc/stdio/http/sse/websocket bindings
  federation/      # publish/discover/connect primitives for entity-owned FP servers
  stores/          # interfaces + memory/sqlite/redis adapters
  policy/          # policy hooks and decisions
  security/        # auth/authz/signature helpers
  observability/   # trace/metrics/token/cost/audit export
  profiles/        # profile presets
  registry/        # schema/event/pattern registries

spec/
  fp-core.schema.json
  fp-openrpc.json

examples/
  quickstart/
  scenarios/

tests/
  unit/
  conformance/
  integration/
  perf/
```

## Production hardening notes

This runtime is intentionally explicit and in-memory-first for clarity.

For production deployment:

- replace in-memory stores with persistent backends
- integrate stronger identity/authn/authz infrastructure
- externalize policy services and key management
- add SLO-backed observability pipelines and alerting

## License

MIT
