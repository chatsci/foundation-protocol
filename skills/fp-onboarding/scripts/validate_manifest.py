#!/usr/bin/env python3
"""Validate FP Skill manifest with bundled schema and semantic checks."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

HANDLER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_\.]*:[A-Za-z_][A-Za-z0-9_]*$")
ENTITY_KINDS = {
    "agent",
    "tool",
    "resource",
    "human",
    "organization",
    "institution",
    "service",
    "ui",
}
CONNECTION_MODES = {"inproc", "http_jsonrpc"}
AUTH_MODES = {"none", "bearer_env", "bearer_static"}


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate FP Skill manifest")
    parser.add_argument("--manifest", type=Path, required=True, help="Path to *.skill.json")
    parser.add_argument(
        "--schema",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "references" / "manifest.schema.json",
        help="Optional schema override path",
    )
    parser.add_argument(
        "--print-normalized",
        action="store_true",
        help="Print normalized JSON on success",
    )
    return parser.parse_args(argv)


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise ValueError(f"file not found: {path}")
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON at {path}: {exc}") from exc
    if not isinstance(raw, dict):
        raise ValueError(f"manifest must be a JSON object: {path}")
    return raw


def validate_schema(raw: dict[str, Any], schema_path: Path) -> None:
    schema = load_json(schema_path)
    try:
        import jsonschema  # type: ignore
    except Exception:
        return
    validator = jsonschema.Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(raw), key=lambda item: list(item.absolute_path))
    if errors:
        first = errors[0]
        path = ".".join(str(item) for item in first.absolute_path) or "<root>"
        raise ValueError(f"schema validation error at {path}: {first.message}")


def _expect_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value


def validate_semantic(raw: dict[str, Any]) -> None:
    _expect_string(raw.get("skill_spec_version"), "skill_spec_version")
    if raw.get("skill_spec_version") != "0.1":
        raise ValueError("skill_spec_version must be 0.1")
    _expect_string(raw.get("fp_version"), "fp_version")

    entity = raw.get("entity")
    if not isinstance(entity, dict):
        raise ValueError("entity must be an object")
    _expect_string(entity.get("entity_id"), "entity.entity_id")
    kind = _expect_string(entity.get("kind"), "entity.kind")
    if kind not in ENTITY_KINDS:
        raise ValueError(f"entity.kind must be one of {sorted(ENTITY_KINDS)}")
    purpose = entity.get("capability_purpose")
    if not isinstance(purpose, list) or not purpose:
        raise ValueError("entity.capability_purpose must be a non-empty list")
    for idx, item in enumerate(purpose):
        _expect_string(item, f"entity.capability_purpose[{idx}]")

    connection = raw.get("connection")
    if not isinstance(connection, dict):
        raise ValueError("connection must be an object")
    mode = _expect_string(connection.get("mode"), "connection.mode")
    if mode not in CONNECTION_MODES:
        raise ValueError(f"connection.mode must be one of {sorted(CONNECTION_MODES)}")
    if mode == "http_jsonrpc":
        _expect_string(connection.get("rpc_url"), "connection.rpc_url")

    auth = raw.get("auth")
    if not isinstance(auth, dict):
        raise ValueError("auth must be an object")
    auth_mode = _expect_string(auth.get("mode"), "auth.mode")
    if auth_mode not in AUTH_MODES:
        raise ValueError(f"auth.mode must be one of {sorted(AUTH_MODES)}")
    if auth_mode == "bearer_env":
        _expect_string(auth.get("token_env"), "auth.token_env")
    if auth_mode == "bearer_static":
        _expect_string(auth.get("token"), "auth.token")

    operations = raw.get("operations")
    if not isinstance(operations, list) or not operations:
        raise ValueError("operations must be a non-empty list")
    seen: set[str] = set()
    for idx, item in enumerate(operations):
        if not isinstance(item, dict):
            raise ValueError(f"operations[{idx}] must be an object")
        name = _expect_string(item.get("name"), f"operations[{idx}].name")
        handler = _expect_string(item.get("handler"), f"operations[{idx}].handler")
        if HANDLER_RE.match(handler) is None:
            raise ValueError(
                f"operations[{idx}].handler must match module.path:function_name"
            )
        if name in seen:
            raise ValueError(f"duplicate operations name: {name}")
        seen.add(name)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    try:
        raw = load_json(args.manifest)
        validate_schema(raw, args.schema)
        validate_semantic(raw)
        if args.print_normalized:
            print(json.dumps(raw, ensure_ascii=False, indent=2, sort_keys=True))
        print("[ok] manifest is valid")
        return 0
    except ValueError as exc:
        print(f"[error] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
