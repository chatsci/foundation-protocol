#!/usr/bin/env bash
set -euo pipefail

PYTHONPATH=src python3 -m examples.quickstart.basic_flow >/dev/null
PYTHONPATH=src python3 -m examples.scenarios.llm_tool_collaboration >/dev/null
PYTHONPATH=src python3 -m examples.scenarios.governed_transfer >/dev/null
PYTHONPATH=src python3 -m examples.scenarios.economy_settlement >/dev/null
PYTHONPATH=src python3 -m examples.scenarios.transport_jsonrpc >/dev/null
