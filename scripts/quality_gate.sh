#!/usr/bin/env bash
set -euo pipefail

bash scripts/run_tests.sh
bash scripts/run_examples.sh
python3 -m compileall -q src tests examples scripts
python3 scripts/validate_specs.py
