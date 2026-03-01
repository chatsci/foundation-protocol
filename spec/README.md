# Foundation Protocol Machine-Readable Spec (v0.1 Draft)

This directory contains machine-readable artifacts that align with the FP v0.1 draft:

- `fp-core.schema.json`: Core object model in JSON Schema Draft 2020-12
- `fp-openrpc.json`: JSON-RPC method surface in OpenRPC format

## Intended Use

These files are intended to be the executable contract for:

- SDK generation and typed client/server scaffolding
- Conformance checks in CI
- Cross-runtime interoperability validation

## Validation

Run local validation from repo root:

```bash
python3 scripts/validate_specs.py
```

Optional flags:

```bash
python3 scripts/validate_specs.py \
  --core spec/fp-core.schema.json \
  --openrpc spec/fp-openrpc.json \
  --draft docs/foundation-protocol-spec-draft.md
```

Validation includes:

- JSON parse checks
- Required FP v0.1 core definitions and method families
- Internal and cross-file `$ref` resolution
- OpenRPC structural checks
- Draft markdown (`fp/*` list) and OpenRPC method alignment checks
- Optional JSON Schema meta-schema validation (if `jsonschema` is installed)

## Versioning Rules

- Increment `info.version` in `fp-openrpc.json` for any API surface change.
- Keep method names stable once published; additions are preferred over breaks.
- Backward-incompatible changes require a new FP minor/major protocol version.
- Keep normative method names synchronized with `docs/foundation-protocol-spec-draft.md`.

## Relationship to White Paper

The white paper establishes goals and architecture principles.  
This folder defines the concrete data and API contracts implementers can code against.
