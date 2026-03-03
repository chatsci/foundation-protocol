#!/usr/bin/env python3
"""Render a starter FP Skill manifest from bundled template."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

TEMPLATE_PATH = Path(__file__).resolve().parents[1] / "assets" / "templates" / "base.skill.json"


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render FP Skill manifest template")
    parser.add_argument("--entity-id", required=True, help="Entity identifier")
    parser.add_argument(
        "--kind",
        default="agent",
        choices=[
            "agent",
            "tool",
            "resource",
            "human",
            "organization",
            "institution",
            "service",
            "ui",
        ],
        help="Entity kind",
    )
    parser.add_argument("--display-name", required=True, help="Entity display name")
    parser.add_argument(
        "--capability",
        action="append",
        default=[],
        help="Capability purpose value (repeatable)",
    )
    parser.add_argument(
        "--operation",
        action="append",
        default=[],
        help="Operation mapping in form name=module.path:function_name (repeatable)",
    )
    parser.add_argument("--output", type=Path, default=None, help="Optional output path")
    return parser.parse_args(argv)


def load_template() -> dict[str, Any]:
    return json.loads(TEMPLATE_PATH.read_text(encoding="utf-8"))


def parse_operations(values: list[str]) -> list[dict[str, Any]]:
    parsed: list[dict[str, Any]] = []
    for item in values:
        if "=" not in item:
            raise ValueError(f"invalid --operation value: {item}")
        name, handler = item.split("=", 1)
        name = name.strip()
        handler = handler.strip()
        if not name or not handler:
            raise ValueError(f"invalid --operation value: {item}")
        parsed.append({"name": name, "handler": handler, "description": None})
    return parsed


def render_manifest(args: argparse.Namespace) -> dict[str, Any]:
    manifest = load_template()
    manifest["entity"]["entity_id"] = args.entity_id
    manifest["entity"]["kind"] = args.kind
    manifest["entity"]["display_name"] = args.display_name
    manifest["entity"]["capability_purpose"] = args.capability or ["example.capability"]
    manifest["defaults"]["default_roles"] = {
        args.entity_id: ["provider"],
        "fp:system:skill-orchestrator": ["coordinator"],
    }
    operations = parse_operations(args.operation) if args.operation else []
    if operations:
        manifest["operations"] = operations
    return manifest


def write_output(manifest: dict[str, Any], output: Path | None) -> None:
    payload = json.dumps(manifest, ensure_ascii=False, indent=2)
    if output is None:
        print(payload)
        return
    output.write_text(payload + "\n", encoding="utf-8")
    print(f"[ok] wrote manifest: {output}")


def main(argv: list[str]) -> int:
    try:
        args = parse_args(argv)
        manifest = render_manifest(args)
        write_output(manifest, args.output)
        return 0
    except ValueError as exc:
        print(f"[error] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
