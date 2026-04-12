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

## Inclusive Gregory As The Example

The current Inclusive Gregory implementation is the clearest example of this pattern.

Inclusive Gregory is configured with a threshold rule plus the other rule objects it needs for allocation, selection, surplus transfer, exclusion, and tie-breaking.
Its constructor helpers make the threshold choice explicit:

- `with_uniform_threshold(...)` configures one threshold for every option.
- `with_option_thresholds(...)` configures an explicit threshold per option.
- `with_threshold_rule(...)` accepts any threshold rule implementation.

That gives one counting method multiple clean entry points without changing the contest input model.
The same `ContestData` can therefore be run under different threshold assumptions just by swapping the threshold rule.

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
