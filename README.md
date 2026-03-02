# Foundation Protocol (FP) - Python Reference Runtime

FP is a graph-first control plane for multi-entity AI systems.

This repository provides a production-ready Python reference runtime for multi-party collaboration, governance, evidence-first operations, and verifiable value exchange.

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

## Skills layer (new)

This repo now includes an isolated skills layer at `skills/` for ultra-low-friction FP onboarding.

What it includes:

- `skills/spec/manifest.schema.json`: `FP Skill Manifest v0.1` schema
- `skills/python/fp_skill/`: Python Skill SDK (`manifest`, `runtime`, `decorators`, `cli`)
- `skills/examples/weather.skill.json`: runnable manifest example

Validate a skill manifest:

```bash
PYTHONPATH=src:skills/python python3 -m fp_skill validate skills/examples/weather.skill.json
```

Run local smoke bootstrap + invoke:

```bash
PYTHONPATH=src:skills/python python3 -m fp_skill smoke skills/examples/weather.skill.json \
  --operation weather.lookup --payload '{"city":"Paris"}'
```

Run with explicit idempotency key (recommended):

```bash
PYTHONPATH=src:skills/python python3 -m fp_skill smoke skills/examples/weather.skill.json \
  --operation weather.lookup --payload '{"city":"Paris"}' \
  --idempotency-key idem-weather-paris-001
```

### Agent-autonomous FP onboarding

The skill design is machine-readable first (`manifest.schema.json` + JSON manifest), so capable agents can self-bootstrap into FP with minimal human operations.

Typical autonomous flow:

1. Agent reads a skill manifest (`*.skill.json`).
2. Agent validates it against the schema.
3. Agent loads handlers and bootstraps `SkillRuntime`.
4. Agent invokes FP operations through `SkillRuntime.invoke(...)`.
5. Agent optionally publishes to network/federation path.

```python
from fp_skill.manifest import load_manifest
from fp_skill.runtime import SkillRuntime

manifest = load_manifest("skills/examples/weather.skill.json")
runtime = SkillRuntime(manifest)
runtime.load_manifest_operations()

result = runtime.invoke(
    operation="weather.lookup",
    input_payload={"city": "Paris"},
    idempotency_key="idem-weather-paris-001",
)
print(result["result"])
```

This means humans only need to define capability + policy defaults once in a manifest; recurring FP wiring can be delegated to agents.

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

Detailed internal codebase guide (repository doc, not published online):

- docs/fp-codebase-guide.md
- docs/fp-skill-deployment-guide-zh.md

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
