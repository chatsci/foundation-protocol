# FP Onboarding Integration Playbook

This playbook explains how to connect an existing runtime to FP with minimal intrusion.

## 1) Define identity and capability boundary

Pick one stable entity identity and keep it stable over time:

- `entity.entity_id`: globally unique ID (for example `fp:agent:weather-bot`)
- `entity.kind`: one of `agent/tool/resource/human/organization/institution/service/ui`
- `entity.capability_purpose`: what this entity can do, not implementation details

## 2) Describe transport and auth

Use `connection` and `auth` as deployment contract:

- local dev:
  - `connection.mode = inproc`
  - `auth.mode = none`
- remote runtime:
  - `connection.mode = http_jsonrpc`
  - `connection.rpc_url = https://...`
  - `auth.mode = bearer_env` or `bearer_static`

## 3) Keep defaults explicit

Set defaults in manifest instead of hidden code paths:

- `defaults.policy_ref`
- `defaults.token_limit`
- `defaults.result_compaction_bytes`
- `defaults.default_roles`

This keeps behavior reproducible across different operators and runtimes.

## 4) Map operations to existing business handlers

Each operation binds one contract name to one handler:

- operation name: protocol-facing capability, such as `weather.lookup`
- handler: runtime import path `module.path:function_name`

Keep the handler thin and reuse existing business logic.

## 5) Validate before runtime

Run local validation first:

```bash
python scripts/validate_manifest.py --manifest weather.skill.json
```

If FP runtime is available, run smoke:

```bash
PYTHONPATH=src:skills/python python3 -m fp_skill smoke weather.skill.json \
  --operation weather.lookup --payload '{"city":"Paris"}'
```

## 6) Production safety

- pass explicit `idempotency_key` for retry-safe calls
- keep auth tokens externalized via env variables
- prefer deterministic manifests with code review
- version manifest changes with the application release

## 7) Non-intrusion principle

FP onboarding should not rewrite your internal model.
Only add:

- one manifest file
- thin operation wrappers
- integration runtime bootstrap

Your core business logic, data model, and orchestration strategy stay unchanged.
