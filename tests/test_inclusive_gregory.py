"""Tests for the first concrete Inclusive Gregory counting method."""

from decimal import Decimal

from ranchovote.methods.inclusive_gregory import InclusiveGregoryCountingMethod
from ranchovote.models import Ballot, ContestData, Option, Participant


def test_selects_options_that_meet_threshold_immediately() -> None:
    """Options that meet their thresholds in the first round are selected."""
    contest_data = ContestData(
        options=(
            Option(
                option_id="solar",
                required_support=Decimal(10),
                title="Solar",
                description="Fund rooftop solar.",
            ),
            Option(
                option_id="bikes",
                required_support=Decimal(10),
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

    result = InclusiveGregoryCountingMethod.configured().run(data=contest_data)

    assert result.selected_option_ids == ("solar", "bikes")


def test_transfers_surplus_to_next_active_preference() -> None:
    """Inclusive Gregory surplus transfers move only the surplus onward."""
    contest_data = ContestData(
        options=(
            Option(
                option_id="alpha",
                required_support=Decimal(10),
                title="Alpha",
                description="Fund alpha.",
            ),
            Option(
                option_id="beta",
                required_support=Decimal(7),
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

    result = InclusiveGregoryCountingMethod.configured().run(data=contest_data)

    assert result.selected_option_ids == ("alpha", "beta")
    assert result.snapshots[0].tallies["alpha"] == Decimal(12)
    assert result.snapshots[1].tallies["beta"] == Decimal(7)


def test_excludes_unselected_option_when_no_surplus_reaches_it() -> None:
    """Options that never reach threshold are excluded after other winners are selected."""
    contest_data = ContestData(
        options=(
            Option(
                option_id="library",
                required_support=Decimal(10),
                title="Library",
                description="Fund the library.",
            ),
            Option(
                option_id="garden",
                required_support=Decimal(10),
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

    result = InclusiveGregoryCountingMethod.configured().run(data=contest_data)

    assert result.selected_option_ids == ("library",)
    assert result.final_state.statuses["garden"].value == "excluded"
