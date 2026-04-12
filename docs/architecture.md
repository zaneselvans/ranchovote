# Architecture

RanChoVote is organized around a simple separation of concerns:

- `ContestData` describes the shared ranked-ballot inputs.
- counting methods and rules describe how those inputs are interpreted.
- `ContestState` tracks the mutable runtime state of one count.
- `ContestResult` and the trace models capture what happened so the run can be inspected later.

The goal of that split is to let the same contest inputs be reused across many kinds of ranked-choice contests without baking one domain's assumptions into the core data model.

## Core Contest Inputs

The core input model is intentionally small.

- `Option` identifies a selectable option and gives it human-readable metadata.
- `Participant` identifies a participant and carries their available weight.
- `Ballot` records a participant's ranking of options.
- `ContestData` validates that those pieces are internally consistent.

These objects are meant to describe the contest itself, not every algorithm-specific interpretation of the contest.
That keeps the core model useful for both classical STV-style elections and more specialized contests such as resource allocation or participatory budgeting.

Participant weight remains part of the core model because it is naturally a property of the participant in many contest types.
For ordinary one-person-one-vote contests, the default weight is `1`, so simple contests remain concise.
Weighted contests can still override it explicitly.

## Thresholds As Method Configuration

Selection thresholds are handled separately from the core contest inputs.

This is an architectural choice: the support required to select an option is often not an intrinsic property of the option itself.
Depending on the contest and the counting method, thresholds may be:

- one contest-wide constant used for every option.
- a per-option mapping supplied as part of a particular run.
- a quota or other derived value computed from contest-wide parameters.
- a dynamic value recalculated as the count progresses.

For that reason, threshold logic lives behind `ThresholdRule` implementations rather than inside `ContestData`.
The input data says what the contest is; the threshold rule says how this particular method interprets selection support.

## Why Some Models Use Pydantic

RanChoVote uses both Pydantic models and standard dataclasses, but they serve different roles.

Pydantic is used at trust boundaries where the code is accepting, validating, or reconstructing structured data.
That is why the core contest-definition models in `models.py` use Pydantic: they describe the immutable inputs to a run, and the rest of the counting code should be able to assume those inputs are internally consistent once validation has succeeded.
Field constraints, cross-object validation, immutability, and serialization support are all valuable there.

Dataclasses are used more heavily for internal runtime and trace objects.
Once a contest has been validated, the counting code mostly needs lightweight containers for mutable state and algorithm-produced records rather than another layer of boundary validation.
For those internal objects, dataclasses keep the code simpler and make mutability more explicit.

In practice, the rule is:

- use Pydantic for validated boundary models such as contest inputs and persisted API-facing read models.
- use dataclasses for internal runtime state and structured records produced by the counting process.

This split is deliberate.
It makes the code communicate which objects are schema-like, validated, and safe to trust versus which objects are plain in-memory state used by the algorithm after validation is complete.

## Naming Method Families And Named Methods

The framework is intentionally more flexible than the set of method names that appear in STV literature.
That flexibility is useful internally, but it also means the code can express many combinations of rules that do not have a standard public name.

RanChoVote therefore uses two different naming levels:

- method families for broad reusable patterns, such as round-based STV counts or iterative counts.
- named methods for specific rule bundles that correspond to recognizable literature or real-world usage.

This distinction matters because a literature-facing name creates expectations outside the repository.
If a method is called `Inclusive Gregory`, readers will reasonably expect more than just one reusable component with that label.
They will expect a coherent STV variant whose overall behavior matches what that name usually implies in practice.

Our policy is:

- use literature-recognizable names only for presets whose rule bundle matches outside expectations closely enough to be honestly described by that name.
- use family or compositional names for flexible framework abstractions that allow non-canonical combinations.
- describe experimental combinations by the rules they use rather than borrowing a canonical name too broadly.

The trace layer follows the same policy.
Persisted run summaries should record both a stable method family identifier and a public method label.
The family identifier stays structural and comparable across related variants, while the public label can be narrower and more honest about whether a run is canonical or descriptive.

In practice, that means a configurable class may implement a family of related counts, while a narrower preset or factory is what should carry a public literature name.
The framework should remain composable, but the names reported in code, traces, and docs should stay faithful to the outside-world meaning of those names.

## Inclusive Gregory As The Example

The current Inclusive Gregory implementation is the clearest example of this pattern.

Inclusive Gregory is configured with a threshold rule plus the other rule objects it needs for allocation, selection, surplus transfer, exclusion, and tie-breaking.
Its constructor helpers make the threshold choice explicit:

- `with_uniform_threshold(...)` configures one threshold for every option.
- `with_option_thresholds(...)` configures an explicit threshold per option.
- `with_threshold_rule(...)` accepts any threshold rule implementation.

That gives one implementation multiple clean entry points without changing the contest input model.
The same `ContestData` can therefore be run under different threshold assumptions just by swapping the threshold rule.

However, this flexibility should not be confused with a guarantee that every configuration is equally well described by the literature-facing name `Inclusive Gregory`.
In STV usage, that name most strongly identifies a recognizable surplus-transfer approach within a broader round-based count.
Some configurations of the framework may therefore be best described compositionally, even if they reuse the same transfer rule.

The practical rule is that the flexible implementation can demonstrate the architecture, but narrower presets should carry the strongest public names.
That keeps the internals reusable while avoiding misleading claims about which combinations correspond to established named methods.

For persisted and displayed runs, this means the Gregory-transfer family can remain stable even when the public label changes.
For example, a run may belong to the `gregory-transfer-stv` family while being labeled either `inclusive-gregory` for the canonical preset or a descriptive variant such as `gregory-transfer-stv (per-option thresholds)` when the configuration is more specialized.

## JSON In Trace Storage

The trace store is intentionally a hybrid of relational tables and serialized structured payloads.
That is a reasonable design because the storage layer serves two different goals at once:

- support analytical queries over runs, events, and snapshots.
- preserve enough structured source data to reconstruct exactly what was counted.

For data that is central to trace analysis, normal relational columns and tables are preferred.
That is why runs, events, and snapshots each have their own tables, and why snapshots are stored one row per option rather than as one opaque document.

Serialized JSON is acceptable when the payload is mainly acting as an audit or reconstruction artifact rather than as the primary target of SQL queries.
In the current design, `selected_option_ids_json`, `details_json`, and especially `contest_data_json` play that role.
They preserve the original structure faithfully without forcing the storage schema to expand every nested field into first-class tables too early.

This is not a license to hide queryable domain data in blobs.
When a field starts to matter for filtering, grouping, joining, or repeated analytical inspection, it should stop being treated as opaque serialized payload.
That is the point where a more structured representation becomes the better design.

In practice, the escalation path is:

- keep JSON serialized as a simple payload when it is mostly used for round-tripping and faithful reconstruction.
- consider DuckDB JSON or nested types such as lists and structs when the database should understand and query into the structure directly.
- move to dedicated relational tables when the stored data becomes a core analytical entity in its own right.

For ranchovote, plain serialized JSON is acceptable today because the trace store is still primarily a reproducibility and comparison tool.
If future analysis needs to query deeply into event details or contest input structure, DuckDB's native JSON or nested types may become a better fit than plain text.
If those structures become central shared entities rather than attached payloads, dedicated tables are the more durable solution.

`contest_data_json` is the field most likely to need that evolution.
It can become large for contests with many participants and ballots, and it will duplicate the same contest definition across runs when several methods or parameter variants are applied to the same input.
If that pattern becomes common, the storage model should likely grow a separate `contests` table keyed by a contest identifier or content hash, with runs referencing that table instead of storing the full contest data inline each time.

## How A Count Runs

At a high level, one contest run works like this:

1. `ContestData` is validated and handed to a configured counting method.
1. The method creates a `ContestState` from those validated inputs.
1. Each round retallies ballots, computes thresholds through the active `ThresholdRule`, and asks the selection and exclusion rules what to do next.
1. Transfers and exclusions update the mutable runtime state.
1. Snapshots and audit events are recorded along the way.
1. The finished `ContestResult` packages the selected options together with the trace of how the result was reached.

This design makes the code easier to explain because each layer has a narrow job.
It also makes the system easier to extend because new contest types usually mean adding or swapping rules, not redesigning the core input model.

## Why This Matters For Exploration

RanChoVote is meant to explore both simple and complex ranked-choice systems.
That works best when the architecture makes the common pieces reusable:

- the same option, participant, and ballot structures can be reused across methods.
- the same state and trace machinery can support very different counting rules.
- new methods can introduce new threshold logic without forcing the input model to change.

In practice, that means the framework can support a straightforward STV-style demonstration, a weighted contest, or a more specialized resource-allocation process while still keeping one understandable conceptual core.
