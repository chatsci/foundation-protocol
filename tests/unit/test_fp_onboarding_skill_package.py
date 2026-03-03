from __future__ import annotations

import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SKILL_DIR = REPO_ROOT / "skills" / "fp-onboarding"


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
    scripts = [
        SKILL_DIR / "scripts" / "validate_manifest.py",
        SKILL_DIR / "scripts" / "render_manifest_template.py",
    ]
    for script in scripts:
        proc = subprocess.run(
            [sys.executable, str(script), "--help"],
            capture_output=True,
            text=True,
            check=False,
        )
        assert proc.returncode == 0, f"{script.name} --help failed: {proc.stderr}"
        assert "usage" in proc.stdout.lower()
