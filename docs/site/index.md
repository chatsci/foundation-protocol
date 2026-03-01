# Foundation Protocol (FP)

FP is a graph-first control plane for multi-entity AI systems.

Use FP when your system is no longer a single model call and starts to look like a society of participants: agents, tools, resources, humans, services, and organizations that need shared coordination, governance, and economic accountability.

## What FP enables

FP gives you a common runtime substrate for:

- multi-party sessions with explicit participants and roles
- stateful activities with strict lifecycle guarantees
- event streams with replay, ack, and backpressure safety
- policy-native governance with provenance evidence
- meter/receipt/settlement/dispute economic primitives
- transport-safe protocol semantics (JSON-RPC ready)

## What can you build with FP

Typical system patterns:

- **LLM workflow platforms**: planner agent + specialized tools + UI renderer in one governed session
- **Enterprise copilots**: high-risk actions gated by human approval and policy evidence
- **Service marketplaces**: execution receipts and settlement references for provider/buyer relationships
- **Multi-agent operations**: role-based collaboration with auditable state transitions
- **Cross-runtime integration**: one control-plane model over heterogeneous frameworks

## Why teams adopt FP

1. **One semantic model** instead of per-framework glue contracts.
2. **Better safety posture** from built-in policy hooks and explicit state transitions.
3. **Lower operational ambiguity** with traceable events and provenance records.
4. **Economic accountability** from first-class metering and receipts.
5. **Scalable integration** via transport-agnostic protocol surfaces.

## FP mental model

Think in six objects:

1. `Entity`: any addressable participant (agent/tool/resource/service/human/org)
2. `Organization`: governance container for role catalogs and policy references
3. `Membership`: role-bearing edge between entity and organization
4. `Session`: multi-party collaboration context with policy and budget
5. `Activity`: unit of execution with canonical state machine
6. `Event`: timeline record for observable behavior and recovery

Core control-plane loop:

1. Register entities.
2. Create a session with participants and roles.
3. Start activities against registered operations.
4. Stream events and ack consumption.
5. Export evidence/economy artifacts when needed.

## FP design principles

- **Graph-first**: participants and relationships are first-class, not hidden in payloads.
- **Multi-party by default**: collaboration is baseline, not a bolt-on mode.
- **Evidence-first**: policy decisions and critical actions produce protocol-visible records.
- **Progressive disclosure**: exchange compact metadata first, fetch heavy artifacts by reference.
- **Profile-oriented evolution**: stable core semantics with extensible runtime profiles.

## Adoption paths

Choose the path that matches your maturity:

### Path A: Quickstart

Use `fp.quickstart` helpers for immediate onboarding and local prototyping.

### Path B: Application Runtime

Use `FPServer` + `FPClient` to build controlled runtime services with explicit session/activity/event governance.

### Path C: Protocol/Transport Integration

Use `fp.transport.http_jsonrpc.JSONRPCDispatcher` to expose FP methods through JSON-RPC APIs.

## Build with token and latency discipline

FP runtime encourages efficient execution:

- compact event payloads
- idempotent retry semantics
- resumable stream consumption
- token/cost metering hooks
- reference-oriented result patterns (`result_ref`)

## Current scope and maturity

- Version: `0.1.0`
- Runtime style: in-memory-first reference implementation
- Recommended usage today: integration baseline, protocol validation, architecture backbone
- Production trajectory: swap stores/transports/policy backends while keeping FP semantics stable

## Where to go next

1. **Start in 15 minutes**: [Getting Started](getting-started.md)
2. **Understand architecture**: [Architecture](architecture.md)
3. **Check white-paper alignment**: [White Paper Alignment](whitepaper-alignment.md)
4. **Run practical scenarios**: [Examples](examples.md)
5. **Review release checklist**: [Release Readiness](release-readiness.md)
6. **Dive into API details**: [API Reference](api.md)
