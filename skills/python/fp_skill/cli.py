"""CLI for FP Skill manifest validation and bootstrap checks."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from enum import Enum

from .errors import SkillError, SkillManifestError
from .manifest import load_manifest
from .runtime import SkillRuntime


def _cmd_validate(args: argparse.Namespace) -> int:
    manifest = load_manifest(args.manifest)
    print(json.dumps(manifest.to_dict(), ensure_ascii=False, indent=2, sort_keys=True))
    print("\n[ok] skill manifest validated")
    return 0


def _cmd_smoke(args: argparse.Namespace) -> int:
    manifest = load_manifest(args.manifest)
    runtime = SkillRuntime(manifest)
    loaded = runtime.load_manifest_operations()
    print(f"[ok] loaded operations: {', '.join(sorted(loaded.keys()))}")
    if args.operation:
        if args.operation not in loaded:
            raise SkillManifestError(f"operation not declared in manifest: {args.operation}")
        payload = json.loads(args.payload) if args.payload else {}
        result = runtime.invoke(
            operation=args.operation,
            input_payload=payload,
            idempotency_key=args.idempotency_key,
        )
        print(json.dumps(_jsonable(result), ensure_ascii=False, indent=2, sort_keys=True))
    return 0


def _jsonable(value: object) -> object:
    if is_dataclass(value):
        return _jsonable(asdict(value))
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    if isinstance(value, tuple):
        return [_jsonable(item) for item in value]
    if isinstance(value, set):
        return [_jsonable(item) for item in sorted(value)]
    return value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="fp-skill", description="FP Skill tooling")
    sub = parser.add_subparsers(dest="cmd", required=True)

    validate = sub.add_parser("validate", help="Validate manifest and print normalized JSON")
    validate.add_argument("manifest", type=Path)
    validate.set_defaults(func=_cmd_validate)

    smoke = sub.add_parser("smoke", help="Load manifest, register operations, optional local invoke")
    smoke.add_argument("manifest", type=Path)
    smoke.add_argument("--operation", type=str, default=None)
    smoke.add_argument("--payload", type=str, default="{}")
    smoke.add_argument("--idempotency-key", type=str, default=None)
    smoke.set_defaults(func=_cmd_smoke)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except SkillError as exc:
        print(f"[error] {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
