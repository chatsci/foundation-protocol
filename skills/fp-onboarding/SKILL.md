---
name: fp-onboarding
description: Use when onboarding an existing agent, tool, service, or organization runtime into Foundation Protocol with low-intrusion integration and a portable, machine-readable skill manifest workflow.
---

# FP Onboarding

## Overview

Use this skill to connect existing logic to FP without rewriting core business code.  
This package is self-contained and portable across Codex and Claude environments.

## Package Contents

- `references/manifest-v0.1.md`: FP Skill manifest specification
- `references/manifest.schema.json`: JSON schema for validation
- `references/integration-playbook.md`: end-to-end integration playbook
- `scripts/validate_manifest.py`: local manifest validator (schema + semantic checks)
- `scripts/render_manifest_template.py`: template renderer for fast bootstrap
- `assets/templates/base.skill.json`: starter manifest template

## Target Outcome

- keep internal logic unchanged
- expose capabilities through FP operations
- validate integration with a reproducible smoke flow

## Quick Workflow

1. Identify integration target
- choose entity kind (`agent`, `tool`, `service`, `organization`, etc.)
- decide stable `entity_id`
- list capability purposes

2. Generate or edit manifest

```bash
python scripts/render_manifest_template.py \
  --entity-id fp:agent:weather-bot \
  --kind agent \
  --display-name "Weather Bot" \
  --capability weather.lookup \
  --operation weather.lookup=weather_handlers:lookup_weather \
  --output weather.skill.json
```

3. Validate manifest

```bash
python scripts/validate_manifest.py --manifest weather.skill.json
```

4. Implement handlers
- map each `operations[].name` to a Python handler
- handler format must be `module.path:function_name`
- keep business logic unchanged; use thin wrapper only

5. (Optional) Run FP runtime smoke check when `fp_skill` is available

```bash
PYTHONPATH=src:skills/python python3 -m fp_skill validate weather.skill.json
PYTHONPATH=src:skills/python python3 -m fp_skill smoke weather.skill.json \
  --operation <operation.name> --payload '{"key":"value"}'
```

6. Production handoff
- if retries are possible, pass explicit `idempotency_key`
- use `http_jsonrpc` mode + bearer/JWT strategy for remote runtime
- keep policy/budget defaults explicit in manifest

## Quick Reference

| Need | Action |
|---|---|
| Add a new capability | Add one `operations[]` entry + one handler function |
| Keep logic non-intrusive | Wrap existing function; avoid business-code rewrites |
| Portable local verification | Run `scripts/validate_manifest.py` |
| FP runtime verification | Run `fp_skill validate/smoke` when available |
| Retry-safe call path | Provide explicit `idempotency_key` |
| Remote connection | Set `connection.mode=http_jsonrpc` and `connection.rpc_url` |

## Common Mistakes

- Using an empty or unstable `entity_id`
- Declaring an operation in manifest without implementing its handler
- Using a handler path that is not importable in runtime environment
- Assuming idempotency is automatic without passing `idempotency_key`
- Mixing protocol redesign tasks with onboarding tasks (this skill is for integration execution)
