from __future__ import annotations

from pathlib import Path

from fp_skill.cli import main


ROOT = Path(__file__).resolve().parents[2]


def test_cli_validate_manifest() -> None:
    rc = main(["validate", str(ROOT / "skills/examples/weather.skill.json")])
    assert rc == 0


def test_cli_smoke_manifest() -> None:
    rc = main(
        [
            "smoke",
            str(ROOT / "skills/examples/weather.skill.json"),
            "--operation",
            "weather.lookup",
            "--payload",
            '{"city":"Tokyo"}',
            "--idempotency-key",
            "idem-cli-weather-001",
        ]
    )
    assert rc == 0
