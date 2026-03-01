# Operations

## Runtime guarantees

FP runtime ships with practical production safeguards:

- strict session/activity state-transition validation
- idempotency fingerprinting for safe retries
- replay + ack event streams with per-stream backpressure
- transport reliability (retry/backoff/jitter/circuit-breaker)
- HTTP keep-alive connection reuse
- cursor pagination for large list APIs
- JSON-safe SQLite persistence with typed decoding

## Quality gates

Run this before release:

```bash
bash scripts/quality_gate.sh
```

This command runs tests, executes runnable examples, validates spec artifacts, and checks Python compilation.

## Documentation workflow

This project uses **MkDocs + Material + mkdocstrings**:

- Markdown pages for architecture and guides
- Automatic API reference from Python source
- Static site output for easy hosting (GitHub Pages, Netlify, internal portal)

Install docs dependencies:

```bash
python3 -m pip install -e ".[docs]"
```

Preview locally:

```bash
bash scripts/serve_docs.sh
```

Build static site:

```bash
bash scripts/build_docs.sh
```

The generated site is written to `site/`.

## CI recommendation

CI workflows:

1. `ci.yml` runs `scripts/quality_gate.sh`.
2. `docs.yml` builds and deploys GitHub Pages using strict MkDocs mode.
