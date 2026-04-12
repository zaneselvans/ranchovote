"""Core package for the ranchovote ranked-choice co-budgeting project.

The package explores how single transferable vote style counting ideas can be adapted
to collaborative budgeting, where participants may contribute different amounts of
funding and options may require different support to succeed. The codebase is split so
that the contest domain model, counting logic, audit trail, serialization formats,
and persisted storage all remain understandable and independently testable.

The main package layout is:

- `ranchovote.models` for validated, immutable contest inputs.
- `ranchovote.state` for mutable runtime state during a count.
- `ranchovote.trace` for structured audit output and persisted read models.
- `ranchovote.contest` for the orchestration entry point.
- `ranchovote.methods` for counting method families and concrete algorithms.
- `ranchovote.rules` for reusable rule components used by methods.
- `ranchovote.io` for text-oriented import and export helpers.
- `ranchovote.storage` for durable trace persistence and retrieval.
- `ranchovote.services`, `ranchovote.web`, and `ranchovote.tui` for shared interface layers.
"""
