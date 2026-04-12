# AGENTS.md

## Scope

This repository is a pre-`1.0` personal side project.
Optimize for clarity, correctness, and forward progress.
Do not preserve backward compatibility unless explicitly asked.

## Project Goals

- Implement understandable Single Transferable Vote style budgeting methods first.
- Use a conceptually simple, named round-based method before Meek.
- Support later experimentation with iterative methods such as Meek.
- Persist election traces for comparison, visualization, and analysis.

## Terminology

Use the neutral framework vocabulary in code, tests, and documentation unless a
module is explicitly discussing STV literature or a budgeting-specific
specialization.

| STV (electoral) | Budgeting                          | Neutral        |
| --------------- | ---------------------------------- | -------------- |
| Election        | Budgeting process                  | Contest        |
| Election result | Budgeting outcome                  | Contest result |
| Candidate       | Project                            | Option         |
| Voter           | Funder, Resident, or Budget Holder | Participant    |
| elect           | fund or approve                    | select         |
| elected         | funded or approved                 | selected       |
| eliminate       | reject                             | exclude        |
| eliminated      | rejected or unfunded               | excluded       |

### Terminology Guidance

- Prefer neutral framework terms like contest, contest result, option, participant, and ballot for core abstractions.
- Use `select` and `exclude` for internal verbs that mutate framework state.
- Reserve electoral words like `elect`, `candidate`, and `voter` for docstrings, comments, or adapters that are explicitly explaining classical STV terminology.
- Reserve budgeting words like `project`, `funder`, and `budget` for the participatory-budgeting specialization rather than the generic core.
- When discussing literature, explain the mapping explicitly: option corresponds to candidate, participant corresponds to voter, select corresponds to elect, and exclude corresponds to eliminate.

## Working Agreements

- Remove dead code and temporary compatibility shims instead of preserving them.
- Prefer canonical literature names for election methods and rules.
- Keep immutable input data separate from mutable election state.
- Keep structured traces as the source of truth; text logs and JSON exports are derived views.
- Update docstrings whenever changing substantive behavior.
- Prefer popular, well-maintained, well-designed, and well-documented open source libraries over bespoke in-repo implementations for common needs.
- Avoid catch-all modules like `utils.py` or `helpers.py`.

## Package Management

- Use `pixi` to run repository tasks and to provide the development interpreter.
- Do not use `pip` directly for installing or syncing project dependencies.
- Keep dependency metadata in `pyproject.toml` and treat `pixi.lock` as the generated lockfile.
- Do not hand-edit `pixi.lock`; regenerate it with `pixi lock` after dependency changes.
- The distribution build still uses Hatch, but it is invoked through `pixi run build-dist` rather than through an interactive Hatch workflow.

## Hook Runner

- Use `prek` to run the repository's pre-commit hooks locally.
- Do not tell agents to run `pre-commit`; it is not part of this project environment.
- `.pre-commit-config.yaml` exists so `prek` can read the hook configuration locally and `pre-commit.ci` can run the same hook set in CI.

## Python Baseline

- Target Python `3.14` and later only.
- Use Python `3.14` features freely.
- Prefer the Pixi-managed interpreter and environment for local development and CI.
- Do not rely on Homebrew, system, or ad hoc local virtualenv interpreters for repository tasks.
- Do not add `from __future__ import annotations`; the project already targets a Python version where it is unnecessary.
- Do not add compatibility code for older Python versions unless explicitly requested.

## Editor Setup

- Open the repository folder directly in VS Code; a checked-in `.code-workspace` file is not required.
- Treat `.vscode/settings.json` as the shared workspace editor configuration.
- Keep editor-generated or personal `*.code-workspace` files out of version control.

## Repository Layout

- `src/ranchovote/models.py`: immutable Pydantic input models.
- `src/ranchovote/state.py`: mutable runtime contest state.
- `src/ranchovote/trace.py`: structured trace records and final results.
- `src/ranchovote/contest.py`: orchestration entry point.
- `src/ranchovote/methods/`: counting-method families and concrete methods.
- `src/ranchovote/rules/`: reusable threshold, allocation, selection, transfer, and elimination rules.
- `src/ranchovote/io/`: text-oriented serialization helpers.
- `src/ranchovote/storage/`: persistent trace storage, with DuckDB as the canonical backend.
- `tests/`: tests mirroring the package layout.
- `docs/`: project notes and user-facing documentation.

## Method Naming

- Use `Inclusive Gregory` for the first concrete round-based method.
- Reserve `IterativeCountingMethod` for Meek-like or Warren-like iterative families.
- Do not use vague names like `simple_stv` for durable modules.

## Trace Persistence

- Use DuckDB for persisted experiment traces.
- Store runs, events, and snapshots in structured tables.
- Prefer queryable tabular data over giant plain-text logs.
- If a trace needs to be shared, export it from the structured store to JSON or another text format.

## Validation Commands

Run the smallest relevant set of checks for the files you changed.

### Python changes

- `pixi run ruff-check`
- `pixi run ruff-format`
- `pixi run tests`
- `pixi run ty-check` when types or interfaces changed materially

### Markdown changes

- `pixi run prek run mdformat --files <changed files>`
- `pixi run prek run markdownlint --files <changed files>`

### TOML and YAML changes

- `pixi run prek run taplo-format`
- `pixi lock` after dependency changes
- `pixi run prek run --files pyproject.toml .pre-commit-config.yaml zensical.toml .github/workflows/*.yml`

### Documentation changes

- `pixi run docs-build`

### Larger multi-file changes

- `pixi run prek run --files <changed files>` when a hook sweep is warranted

## Testing Expectations

- Add or update tests with new behavior whenever practical.
- Favor small deterministic fixtures over large opaque datasets.
- Mirror test module names to the implementation modules they cover.
- For contest methods, include both happy-path and transfer/elimination edge cases.

## Notes For Agents

- Before adding a new abstraction, check whether an existing `rules/` or `methods/` module is the better home.
- Keep imports absolute within `src/ranchovote`.
- Do not reintroduce `src/ranchovote/ranchovote.py`.
