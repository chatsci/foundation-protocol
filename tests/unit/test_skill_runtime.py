from __future__ import annotations

from fp_skill.manifest import SkillManifest
from fp_skill.runtime import SkillRuntime


def _manifest() -> SkillManifest:
    return SkillManifest.from_dict(
        {
            "skill_spec_version": "0.1",
            "fp_version": "0.1.0",
            "entity": {
                "entity_id": "fp:agent:weather-skill-runtime",
                "kind": "agent",
                "capability_purpose": ["weather.lookup"],
            },
            "connection": {"mode": "inproc"},
            "auth": {"mode": "none"},
            "defaults": {
                "auto_session": True,
                "policy_ref": "policy:test",
                "token_limit": 4096,
                "result_compaction_bytes": 4096,
                "default_roles": {
                    "fp:agent:weather-skill-runtime": ["provider"],
                    "fp:system:skill-orchestrator": ["coordinator"],
                },
            },
            "operations": [
                {
                    "name": "weather.lookup",
                    "handler": "skills.examples.weather_handlers:lookup_weather",
                }
            ],
        }
    )


def test_skill_runtime_load_and_invoke() -> None:
    runtime = SkillRuntime(_manifest())
    loaded = runtime.load_manifest_operations()
    assert "weather.lookup" in loaded

    result = runtime.invoke(operation="weather.lookup", input_payload={"city": "Berlin"})
    assert result["activity"].state.value == "completed"
    assert result["result"]["city"] == "Berlin"
    assert result["result"]["temp_c"] == 22


def test_skill_runtime_inproc_client() -> None:
    runtime = SkillRuntime(_manifest())
    client = runtime.client()
    ping = client.ping()
    assert ping["ok"] is True
    assert "fp_version" in ping


def test_skill_runtime_default_invoke_is_not_idempotent() -> None:
    runtime = SkillRuntime(_manifest())
    runtime.load_manifest_operations()

    first = runtime.invoke(operation="weather.lookup", input_payload={"city": "Rome"})
    second = runtime.invoke(operation="weather.lookup", input_payload={"city": "Rome"})

    assert first["activity"].activity_id != second["activity"].activity_id


def test_skill_runtime_explicit_idempotency_key_reuses_activity() -> None:
    runtime = SkillRuntime(_manifest())
    runtime.load_manifest_operations()

    first = runtime.invoke(
        operation="weather.lookup",
        input_payload={"city": "Madrid"},
        idempotency_key="idem-weather-madrid-001",
    )
    second = runtime.invoke(
        operation="weather.lookup",
        input_payload={"city": "Madrid"},
        idempotency_key="idem-weather-madrid-001",
    )

    assert first["activity"].activity_id == second["activity"].activity_id
