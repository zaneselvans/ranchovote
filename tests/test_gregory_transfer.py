"""Tests for the Gregory-transfer counting method family."""

from decimal import Decimal

from ranchovote.methods.gregory_transfer import InclusiveGregoryCountingMethod
from ranchovote.models import Ballot, ContestData, Option, Participant


def test_selects_options_that_meet_threshold_immediately() -> None:
    """Options that meet their thresholds in the first round are selected."""
    contest_data = ContestData(
        options=(
            Option(
                option_id="solar",
                title="Solar",
                description="Fund rooftop solar.",
            ),
            Option(
                option_id="bikes",
                title="Bikes",
                description="Fund bike parking.",
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
                weight=Decimal(10),
            ),
        ),
        ballots=(
            Ballot(participant_id="alice", ranking=("solar", "bikes")),
            Ballot(participant_id="bob", ranking=("bikes", "solar")),
        ),
    )

    result = InclusiveGregoryCountingMethod.with_uniform_threshold(
        threshold=Decimal(10)
    ).run(data=contest_data)

    assert result.selected_option_ids == ("solar", "bikes")


def test_transfers_surplus_to_next_active_preference() -> None:
    """Inclusive Gregory surplus transfers move only the surplus onward."""
    contest_data = ContestData(
        options=(
            Option(
                option_id="alpha",
                title="Alpha",
                description="Fund alpha.",
            ),
            Option(
                option_id="beta",
                title="Beta",
                description="Fund beta.",
            ),
        ),
        participants=(
            Participant(
                participant_id="anna",
                name="Anna",
                weight=Decimal(6),
            ),
            Participant(
                participant_id="ben",
                name="Ben",
                weight=Decimal(6),
            ),
            Participant(
                participant_id="cara",
                name="Cara",
                weight=Decimal(5),
            ),
        ),
        ballots=(
            Ballot(participant_id="anna", ranking=("alpha", "beta")),
            Ballot(participant_id="ben", ranking=("alpha", "beta")),
            Ballot(participant_id="cara", ranking=("beta", "alpha")),
        ),
    )

    result = InclusiveGregoryCountingMethod.with_option_thresholds(
        thresholds_by_option={
            "alpha": Decimal(10),
            "beta": Decimal(7),
        }
    ).run(data=contest_data)

    assert result.selected_option_ids == ("alpha", "beta")
    assert result.snapshots[0].tallies["alpha"] == Decimal(12)
    assert result.snapshots[1].tallies["beta"] == Decimal(7)


def test_excludes_unselected_option_when_no_surplus_reaches_it() -> None:
    """Options that never reach threshold are excluded after other winners are selected."""
    contest_data = ContestData(
        options=(
            Option(
                option_id="library",
                title="Library",
                description="Fund the library.",
            ),
            Option(
                option_id="garden",
                title="Garden",
                description="Fund the garden.",
            ),
        ),
        participants=(
            Participant(
                participant_id="ada",
                name="Ada",
                weight=Decimal(5),
            ),
            Participant(
                participant_id="bert",
                name="Bert",
                weight=Decimal(5),
            ),
            Participant(
                participant_id="cleo",
                name="Cleo",
                weight=Decimal(5),
            ),
        ),
        ballots=(
            Ballot(participant_id="ada", ranking=("library", "garden")),
            Ballot(participant_id="bert", ranking=("library", "garden")),
            Ballot(participant_id="cleo", ranking=("garden", "library")),
        ),
    )

    result = InclusiveGregoryCountingMethod.with_uniform_threshold(
        threshold=Decimal(10)
    ).run(data=contest_data)

    assert result.selected_option_ids == ("library",)
    assert result.final_state.statuses["garden"].value == "excluded"


def test_uses_default_participant_weight_for_classical_stv_style_inputs() -> None:
    """Participants can omit weight when a contest uses one-person-one-vote inputs."""
    contest_data = ContestData(
        options=(
            Option(
                option_id="alpha",
                title="Alpha",
                description="Alpha option.",
            ),
            Option(
                option_id="beta",
                title="Beta",
                description="Beta option.",
            ),
        ),
        participants=(
            Participant(
                participant_id="alice",
                name="Alice",
            ),
            Participant(
                participant_id="bob",
                name="Bob",
            ),
        ),
        ballots=(
            Ballot(participant_id="alice", ranking=("alpha", "beta")),
            Ballot(participant_id="bob", ranking=("beta", "alpha")),
        ),
    )

    result = InclusiveGregoryCountingMethod.with_uniform_threshold(
        threshold=Decimal(1)
    ).run(data=contest_data)

    assert contest_data.participants[0].weight == Decimal(1)
    assert result.selected_option_ids == ("alpha", "beta")
