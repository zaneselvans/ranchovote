# RanChoVote

RanChoVote is a Python project for experimenting with ranked collective-decision methods built from Single Transferable Vote ideas. The current codebase focuses on a neutral contest model that can support participatory budgeting, classical STV-style elections, and related selection problems without baking one domain vocabulary into the core abstractions.

The repository currently includes:

- immutable contest input models under `src/ranchovote/models.py`
- mutable counting state and structured trace output under `src/ranchovote/state.py` and `src/ranchovote/trace.py`
- a first concrete round-based method using Gregory-transfer STV under `src/ranchovote/methods/gregory_transfer.py`, with the canonical Inclusive Gregory preset exposed from that family module
- DuckDB-backed trace persistence under `src/ranchovote/storage/`
- FastAPI and Textual trace explorers launched from the CLI in `src/ranchovote/cli.py`

## Development

This repository is set up around Pixi.

Common commands:

```shell
pixi run test
pixi run ruff-check
pixi run ruff-format
pixi run typecheck
pixi run docs-build
pixi run build-dist
```

## Documentation

The docs site is built with Zensical and mkdocstrings:

```shell
pixi run docs-build
```

Hand-written pages live under `docs/`. The API reference is generated during the docs build from `src/ranchovote/` and `scripts/gen_ref_pages.py`.
