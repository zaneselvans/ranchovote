"""Tests for contest models, state, and reusable counting rules."""

from decimal import Decimal

import pytest

from ranchovote.methods.inclusive_gregory import InclusiveGregoryCountingMethod
from ranchovote.methods.meek import MeekCountingMethod
from ranchovote.models import Ballot, ContestData, Option, Participant
from ranchovote.rules.allocation import FirstActivePreferenceAllocationRule
from ranchovote.rules.elimination import (
    InputOrderTieBreakRule,
    LowestTallyEliminationRule,
)
from ranchovote.rules.selection import ThresholdSelectionRule
from ranchovote.rules.thresholds import RequiredSupportThresholdRule
from ranchovote.rules.transfers import InclusiveGregorySurplusTransferRule
from ranchovote.state import ContestState, OptionStatus
from ranchovote.trace import TracePhaseType


def build_contest_data() -> ContestData:
    """Return a small valid contest fixture for rule tests."""
    return ContestData(
        options=(
            Option(
                option_id="alpha",
                required_support=Decimal(10),
                title="Alpha",
                description="Fund alpha.",
            ),
            Option(
                option_id="beta",
                required_support=Decimal(5),
                title="Beta",
                description="Fund beta.",
            ),
        ),
        participants=(
            Participant(
                participant_id="alice",
                name="Alice",
                weight=Decimal(10),
            ),
            Participant(
                participant_id="bob",
                name="Bob",
                weight=Decimal(5),
            ),
        ),
        ballots=(
            Ballot(participant_id="alice", ranking=("alpha", "beta")),
            Ballot(participant_id="bob", ranking=("beta", "alpha")),
        ),
    )


def test_ballot_rejects_duplicate_rankings() -> None:
    """Ballots should reject repeated option IDs."""
    with pytest.raises(ValueError, match="must not contain duplicate"):
        Ballot(participant_id="alice", ranking=("alpha", "alpha"))


@pytest.mark.parametrize(
    ("options", "participants", "ballots", "message"),
    [
        pytest.param(
            (
                Option(
                    option_id="dup",
                    required_support=Decimal(1),
                    title="One",
                    description="One.",
                ),
                Option(
                    option_id="dup",
                    required_support=Decimal(2),
                    title="Two",
                    description="Two.",
                ),
            ),
            (
                Participant(
                    participant_id="alice",
                    name="Alice",
                    weight=Decimal(1),
                ),
            ),
            (),
            "Option IDs must be unique",
            id="duplicate-options",
        ),
        pytest.param(
            (
                Option(
                    option_id="alpha",
                    required_support=Decimal(1),
                    title="Alpha",
                    description="Alpha.",
                ),
            ),
            (
                Participant(
                    participant_id="dup",
                    name="Alice",
                    weight=Decimal(1),
                ),
                Participant(
                    participant_id="dup",
                    name="Bob",
                    weight=Decimal(1),
                ),
            ),
            (),
            "Participant IDs must be unique",
            id="duplicate-participants",
        ),
        pytest.param(
            (
                Option(
                    option_id="alpha",
                    required_support=Decimal(1),
                    title="Alpha",
                    description="Alpha.",
                ),
            ),
            (
                Participant(
                    participant_id="alice",
                    name="Alice",
                    weight=Decimal(1),
                ),
            ),
            (Ballot(participant_id="bob", ranking=("alpha",)),),
            "Ballot participant_id values must refer",
            id="unknown-participant",
        ),
        pytest.param(
            (
                Option(
                    option_id="alpha",
                    required_support=Decimal(1),
                    title="Alpha",
                    description="Alpha.",
                ),
            ),
            (
                Participant(
                    participant_id="alice",
                    name="Alice",
                    weight=Decimal(1),
                ),
            ),
            (
                Ballot(participant_id="alice", ranking=("alpha",)),
                Ballot(participant_id="alice", ranking=("alpha",)),
            ),
            "at most one ballot",
            id="duplicate-ballots",
        ),
        pytest.param(
            (
                Option(
                    option_id="alpha",
                    required_support=Decimal(1),
                    title="Alpha",
                    description="Alpha.",
                ),
            ),
            (
                Participant(
                    participant_id="alice",
                    name="Alice",
                    weight=Decimal(1),
                ),
            ),
            (Ballot(participant_id="alice", ranking=("missing",)),),
            "Unknown values: missing",
            id="unknown-option",
        ),
    ],
)
def test_contest_data_rejects_invalid_inputs(
    options: tuple[Option, ...],
    participants: tuple[Participant, ...],
    ballots: tuple[Ballot, ...],
    message: str,
) -> None:
    """ContestData should reject inconsistent option, participant, and ballot inputs."""
    with pytest.raises(ValueError, match=message):
        ContestData(options=options, participants=participants, ballots=ballots)


def test_contest_data_lookup_helpers_return_values_and_raise_on_unknown_ids() -> None:
    """Lookup helpers should return known objects and raise for unknown IDs."""
    data = build_contest_data()

    assert data.option_by_id("alpha").title == "Alpha"
    assert data.participant_by_id("alice").name == "Alice"

    with pytest.raises(KeyError, match="Unknown option_id"):
        data.option_by_id("missing")

    with pytest.raises(KeyError, match="Unknown participant_id"):
        data.participant_by_id("missing")


def test_counting_method_base_classes_expose_names_and_initial_state() -> None:
    """Configured counting methods should expose their names and seed runtime state."""
    data = build_contest_data()

    inclusive_gregory = InclusiveGregoryCountingMethod.configured()
    assert inclusive_gregory.name == "inclusive-gregory"
    assert inclusive_gregory.initial_state(data=data).active_option_ids() == (
        "alpha",
        "beta",
    )

    meek = MeekCountingMethod(
        threshold_rule=RequiredSupportThresholdRule(),
        ballot_allocation_rule=FirstActivePreferenceAllocationRule(),
        selection_rule=ThresholdSelectionRule(),
        tie_break_rule=InputOrderTieBreakRule(),
        convergence_tolerance=Decimal("0.001"),
        max_iterations=10,
        method_name="meek",
    )
    assert meek.name == "meek"
    assert meek.initial_state(data=data).active_option_ids() == ("alpha", "beta")

    with pytest.raises(NotImplementedError, match="not implemented"):
        meek.run(data=data)


def test_state_records_initial_and_iteration_phase_metadata() -> None:
    """State trace helpers should emit initial and iterative phase metadata correctly."""
    data = build_contest_data()
    initial_state = ContestState.from_data(data)

    initial_state.record_event(event_type="initial", message="Initial event")
    initial_state.capture_snapshot({"alpha": Decimal(10), "beta": Decimal(5)})

    assert initial_state.audit_log[0].phase_type == TracePhaseType.INITIAL
    assert initial_state.audit_log[0].round_number is None
    assert initial_state.snapshots[0].phase_type == TracePhaseType.INITIAL

    iteration_state = ContestState.from_data(data)
    iteration_state.iteration_number = 2
    iteration_state.record_event(event_type="iteration", message="Iteration event")
    iteration_state.capture_snapshot({"alpha": Decimal(10), "beta": Decimal(5)})

    assert iteration_state.audit_log[0].phase_type == TracePhaseType.ITERATION
    assert iteration_state.audit_log[0].phase_index == 2
    assert iteration_state.snapshots[0].phase_type == TracePhaseType.ITERATION


def test_first_active_preference_allocation_handles_success_and_errors() -> None:
    """Ballot allocation should honor active preferences and reject invalid state."""
    data = build_contest_data()
    ballot = data.ballots[0]
    state = ContestState.from_data(data)
    rule = FirstActivePreferenceAllocationRule()

    assert rule.allocation_for_ballot(ballot=ballot, data=data, state=state) == {
        "alpha": Decimal(10)
    }

    state.statuses["alpha"] = OptionStatus.SELECTED
    state.statuses["beta"] = OptionStatus.SELECTED
    assert rule.allocation_for_ballot(ballot=ballot, data=data, state=state) == {}

    missing_weight_state = ContestState.from_data(data)
    del missing_weight_state.ballot_weights["alice"]
    with pytest.raises(ValueError, match="Missing ballot weight"):
        rule.allocation_for_ballot(ballot=ballot, data=data, state=missing_weight_state)

    missing_status_state = ContestState.from_data(data)
    del missing_status_state.statuses["alpha"]
    with pytest.raises(ValueError, match="Missing option status"):
        rule.allocation_for_ballot(ballot=ballot, data=data, state=missing_status_state)


def test_selection_and_elimination_rules_cover_success_and_failure_paths() -> None:
    """Selection and elimination rules should handle normal and invalid states."""
    data = build_contest_data()
    state = ContestState.from_data(data)
    state.tallies["alpha"] = Decimal(10)
    state.tallies["beta"] = Decimal(3)

    selection_rule = ThresholdSelectionRule()
    thresholds = {"alpha": Decimal(10), "beta": Decimal(5)}
    assert selection_rule.select_options(
        data=data,
        state=state,
        thresholds=thresholds,
    ) == ("alpha",)

    missing_status_state = ContestState.from_data(data)
    del missing_status_state.statuses["alpha"]
    with pytest.raises(ValueError, match="Missing option status"):
        selection_rule.select_options(
            data=data,
            state=missing_status_state,
            thresholds=thresholds,
        )

    with pytest.raises(ValueError, match="Missing threshold"):
        selection_rule.select_options(
            data=data,
            state=ContestState.from_data(data),
            thresholds={"alpha": Decimal(10)},
        )

    elimination_rule = LowestTallyEliminationRule()
    tie_break_rule = InputOrderTieBreakRule()
    assert (
        elimination_rule.exclude_option(
            data=data,
            state=state,
            thresholds=thresholds,
            tie_break_rule=tie_break_rule,
        )
        == "beta"
    )

    tied_state = ContestState.from_data(data)
    tied_state.tallies["alpha"] = Decimal(1)
    tied_state.tallies["beta"] = Decimal(1)
    assert (
        elimination_rule.exclude_option(
            data=data,
            state=tied_state,
            thresholds=thresholds,
            tie_break_rule=tie_break_rule,
        )
        == "alpha"
    )

    empty_state = ContestState.from_data(data)
    empty_state.statuses = dict.fromkeys(empty_state.statuses, OptionStatus.SELECTED)
    with pytest.raises(ValueError, match="no active options"):
        elimination_rule.exclude_option(
            data=data,
            state=empty_state,
            thresholds=thresholds,
            tie_break_rule=tie_break_rule,
        )

    with pytest.raises(ValueError, match="must all appear"):
        tie_break_rule.break_tie(
            option_ids=("missing",),
            data=data,
            state=state,
            reason="test",
        )


def test_surplus_transfer_rule_covers_guardrails_and_event_recording() -> None:
    """Inclusive Gregory transfers should clamp values and reject invalid state."""
    data = build_contest_data()
    state = ContestState.from_data(data)
    state.ballot_allocations = {"alice": {"alpha": Decimal(10)}}
    state.tallies["alpha"] = Decimal(10)
    thresholds = {"alpha": Decimal(5), "beta": Decimal(5)}
    rule = InclusiveGregorySurplusTransferRule()

    rule.apply_surplus_transfers(
        selected_option_ids=("alpha",),
        data=data,
        state=state,
        thresholds=thresholds,
    )

    assert state.keep_factors["alpha"] == Decimal("0.5")
    assert state.ballot_weights["alice"] == Decimal(5)
    assert state.audit_log[-1].event_type == "surplus-transfer"

    assert rule._keep_factor(current_tally=Decimal(0), threshold=Decimal(5)) == Decimal(
        0
    )
    assert rule._keep_factor(current_tally=Decimal(4), threshold=Decimal(5)) == Decimal(
        1
    )

    with pytest.raises(ValueError, match="Missing threshold"):
        rule._option_transfer_inputs(
            option_id="alpha",
            state=state,
            thresholds={},
        )

    missing_tally_state = ContestState.from_data(data)
    del missing_tally_state.tallies["alpha"]
    with pytest.raises(ValueError, match="Missing tally"):
        rule._option_transfer_inputs(
            option_id="alpha",
            state=missing_tally_state,
            thresholds=thresholds,
        )

    missing_weight_state = ContestState.from_data(data)
    missing_weight_state.ballot_allocations = {"alice": {"alpha": Decimal(1)}}
    del missing_weight_state.ballot_weights["alice"]
    with pytest.raises(ValueError, match="Missing ballot weight"):
        rule._update_ballot_weights(
            keep_factor=Decimal("0.5"),
            option_id="alpha",
            state=missing_weight_state,
        )

    negative_allocation_state = ContestState.from_data(data)
    negative_allocation_state.ballot_allocations = {"alice": {"alpha": Decimal(-1)}}
    with pytest.raises(ValueError, match="must be non-negative"):
        rule._update_ballot_weights(
            keep_factor=Decimal("0.5"),
            option_id="alpha",
            state=negative_allocation_state,
        )

    negative_weight_state = ContestState.from_data(data)
    negative_weight_state.ballot_allocations = {"alice": {"alpha": Decimal(10)}}
    negative_weight_state.ballot_weights["alice"] = Decimal(1)
    with pytest.raises(ValueError, match="became negative"):
        rule._update_ballot_weights(
            keep_factor=Decimal(2),
            option_id="alpha",
            state=negative_weight_state,
        )
