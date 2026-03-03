# FP Skill Manifest v0.1

`FP Skill Manifest` is a language-agnostic description for auto-bootstraping entities into FP.

## Design goals

- Keep manifest compact and stable.
- Make skill layer depend on FP protocol, not inverse.
- Enable deterministic validation before runtime.

## Top-level fields

- `skill_spec_version`: currently fixed at `0.1`.
- `fp_version`: expected FP runtime version (for compatibility checks).
- `entity`: entity identity and capability summary.
- `connection`: where skill runtime should connect (`inproc` / `http_jsonrpc`).
- `auth`: bearer credential strategy (`none` / `bearer_env` / `bearer_static`).
- `defaults`: policy/budget/runtime defaults for session and compaction.
- `operations`: operation mapping list (`name` + `handler`).

## Handler format

`operations[].handler` must be `module.path:function_name`.

Example:

- `skills.examples.weather_handlers:lookup_weather`

## Minimal manifest example

```json
{
  "skill_spec_version": "0.1",
  "fp_version": "0.1.0",
  "entity": {
    "entity_id": "fp:agent:weather-bot",
    "kind": "agent",
    "display_name": "Weather Bot",
    "capability_purpose": ["weather.lookup"]
  },
  "connection": {
    "mode": "inproc"
  },
  "auth": {
    "mode": "none"
  },
  "defaults": {
    "auto_session": true,
    "policy_ref": "policy:default",
    "token_limit": 4096,
    "result_compaction_bytes": 4096,
    "default_roles": {
      "fp:agent:weather-bot": ["provider"],
      "fp:system:skill-orchestrator": ["coordinator"]
    }
  },
  "operations": [
    {
      "name": "weather.lookup",
      "handler": "skills.examples.weather_handlers:lookup_weather"
    }
  ]
}
```
