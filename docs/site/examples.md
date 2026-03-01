# Examples

All examples are runnable and covered by smoke tests.

## Run all examples

```bash
bash scripts/run_examples.sh
```

## Available examples

### 1) Basic quickstart

File: `examples/quickstart/basic_flow.py`

Shows:

- entity registration
- session creation
- operation registration
- synchronous activity completion

Run:

```bash
PYTHONPATH=src python3 -m examples.quickstart.basic_flow
```

### 2) LLM + tool collaboration

File: `examples/scenarios/llm_tool_collaboration.py`

Shows:

- multi-tool session orchestration
- chaining activity outputs across tools
- planner/provider role collaboration

Run:

```bash
PYTHONPATH=src python3 -m examples.scenarios.llm_tool_collaboration
```

### 3) Governed high-risk transfer

File: `examples/scenarios/governed_transfer.py`

Shows:

- policy denial path
- approval-gated invocation
- allowed/denied decision evidence

Run:

```bash
PYTHONPATH=src python3 -m examples.scenarios.governed_transfer
```

### 4) Economy settlement flow

File: `examples/scenarios/economy_settlement.py`

Shows:

- metering record creation
- receipt issuance and integrity verification
- settlement creation and confirmation

Run:

```bash
PYTHONPATH=src python3 -m examples.scenarios.economy_settlement
```

### 5) JSON-RPC transport integration

File: `examples/scenarios/transport_jsonrpc.py`

Shows:

- `JSONRPCDispatcher.from_server(...)`
- JSON-RPC `fp/ping` success path
- structured mapping for FP semantic errors

Run:

```bash
PYTHONPATH=src python3 -m examples.scenarios.transport_jsonrpc
```
