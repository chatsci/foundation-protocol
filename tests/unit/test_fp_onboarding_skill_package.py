from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SKILL_DIR = REPO_ROOT / "skills" / "fp-onboarding"
RENDER_SCRIPT = SKILL_DIR / "scripts" / "render_manifest_template.py"
VALIDATE_SCRIPT = SKILL_DIR / "scripts" / "validate_manifest.py"


def _run_script(script: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(script), *args],
        capture_output=True,
        text=True,
        check=False,
    )


def test_portable_skill_bundle_structure() -> None:
    expected = [
        SKILL_DIR / "SKILL.md",
        SKILL_DIR / "references" / "manifest-v0.1.md",
        SKILL_DIR / "references" / "manifest.schema.json",
        SKILL_DIR / "references" / "integration-playbook.md",
        SKILL_DIR / "scripts" / "validate_manifest.py",
        SKILL_DIR / "scripts" / "render_manifest_template.py",
        SKILL_DIR / "assets" / "templates" / "base.skill.json",
        SKILL_DIR / "agents" / "openai.yaml",
    ]
    for path in expected:
        assert path.exists(), f"missing skill package file: {path}"


def test_skill_md_is_portable_and_repo_agnostic() -> None:
    skill_md = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
    # Portable skill should avoid hard-coding monorepo-relative paths.
    assert "skills/spec/" not in skill_md
    assert "skills/examples/" not in skill_md


def test_bundle_scripts_are_runnable_help() -> None:
    scripts = [VALIDATE_SCRIPT, RENDER_SCRIPT]
    for script in scripts:
        proc = _run_script(script, "--help")
        assert proc.returncode == 0, f"{script.name} --help failed: {proc.stderr}"
        assert "usage" in proc.stdout.lower()


def test_render_template_requires_at_least_one_operation(tmp_path: Path) -> None:
    output = tmp_path / "manifest.skill.json"
    proc = _run_script(
        RENDER_SCRIPT,
        "--entity-id",
        "fp:agent:demo",
        "--kind",
        "agent",
        "--display-name",
        "Demo Agent",
        "--capability",
        "demo.capability",
        "--output",
        str(output),
    )
    assert proc.returncode != 0
    assert "operation" in proc.stderr.lower()
    assert not output.exists()


def test_validate_defaults_auto_session_requires_roles(tmp_path: Path) -> None:
    manifest = json.loads((SKILL_DIR / "assets" / "templates" / "base.skill.json").read_text(encoding="utf-8"))
    manifest["entity"]["entity_id"] = "fp:agent:demo"
    manifest["entity"]["kind"] = "agent"
    manifest["entity"]["display_name"] = "Demo Agent"
    manifest["entity"]["capability_purpose"] = ["demo.capability"]
    manifest["operations"] = [{"name": "demo.run", "handler": "demo.handlers:run", "description": None}]
    manifest["defaults"]["auto_session"] = True
    manifest["defaults"]["default_roles"] = {}
    file_path = tmp_path / "bad-default-roles.skill.json"
    file_path.write_text(json.dumps(manifest), encoding="utf-8")

    proc = _run_script(VALIDATE_SCRIPT, "--manifest", str(file_path))
    assert proc.returncode != 0
    assert "default_roles" in proc.stderr


def test_validate_defaults_token_limit_must_be_positive(tmp_path: Path) -> None:
    manifest = json.loads((SKILL_DIR / "assets" / "templates" / "base.skill.json").read_text(encoding="utf-8"))
    manifest["entity"]["entity_id"] = "fp:agent:demo"
    manifest["entity"]["kind"] = "agent"
    manifest["entity"]["display_name"] = "Demo Agent"
    manifest["entity"]["capability_purpose"] = ["demo.capability"]
    manifest["operations"] = [{"name": "demo.run", "handler": "demo.handlers:run", "description": None}]
    manifest["defaults"]["token_limit"] = 0
    file_path = tmp_path / "bad-token-limit.skill.json"
    file_path.write_text(json.dumps(manifest), encoding="utf-8")

    proc = _run_script(VALIDATE_SCRIPT, "--manifest", str(file_path))
    assert proc.returncode != 0
    assert "token_limit" in proc.stderr
