# FP Skills (Monorepo Isolated Layer)

This directory contains the FP Skill layer, intentionally isolated from `src/fp` core runtime.

## Design rules

- Skills depend on FP protocol/runtime APIs.
- FP core does not depend on skills.
- Manifest-driven bootstrap is the default integration path.
- Codex/Claude ecosystem skill lives at `skills/fp-onboarding/SKILL.md`.

## Structure

```text
skills/
  fp-onboarding/
    SKILL.md
  spec/
    manifest.schema.json
    manifest-v0.1.md
  examples/
    weather.skill.json
    weather_handlers.py
  python/
    fp_skill/
      manifest.py
      runtime.py
      decorators.py
      cli.py
```

## Portable skill package (Codex + Claude)

`skills/fp-onboarding/` is a self-contained package:

- `SKILL.md`: onboarding workflow and decision guide
- `references/`: spec, schema, and integration playbook
- `scripts/`: manifest generation and validation utilities
- `assets/templates/`: manifest starter template
- `agents/openai.yaml`: UI metadata

This makes the skill portable to:

- Codex: `~/.codex/skills/fp-onboarding/`
- Claude Code: `~/.claude/skills/fp-onboarding/`

## Quick start

Validate manifest:

```bash
PYTHONPATH=src:skills/python python3 -m fp_skill validate skills/examples/weather.skill.json
```

Smoke bootstrap and local invoke:

```bash
PYTHONPATH=src:skills/python python3 -m fp_skill smoke skills/examples/weather.skill.json \
  --operation weather.lookup --payload '{"city":"Paris"}'
```

Smoke with explicit idempotency key (recommended for retry-safe callers):

```bash
PYTHONPATH=src:skills/python python3 -m fp_skill smoke skills/examples/weather.skill.json \
  --operation weather.lookup --payload '{"city":"Paris"}' \
  --idempotency-key idem-weather-paris-001
```

## Runtime behavior notes

- Skill runtime auto-registers the manifest entity and orchestrator entity.
- If `defaults.auto_session=true`, runtime auto-creates/reuses one session.
- Idempotency is opt-in: `idempotency_key` must be supplied explicitly.
  - no key => each invoke creates a new activity
  - same key + same fingerprint => activity result reuse
  - same key + different fingerprint => conflict

## Why this exists

Skill layer reduces FP adoption friction:

- auto-load entity + operation metadata from manifest
- auto-register entity and operations
- auto-create governed session (when enabled)
- keep protocol semantics in FP core unchanged
