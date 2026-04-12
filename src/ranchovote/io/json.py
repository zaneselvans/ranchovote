"""JSON-oriented serializers for contest inputs and trace outputs.

These helpers flatten Pydantic models, dataclasses, enums, and decimals into shapes
that are straightforward to emit from APIs, save in files, or inspect in tests. They
do not decide where data is stored; they only define how ranchovote objects are exposed
in a JSON-friendly form.
"""

from decimal import Decimal
from typing import TypedDict

from ranchovote.models import ContestData
from ranchovote.trace import ContestResult, CountEvent, RoundSnapshot


class OptionJson(TypedDict):
    """JSON shape for one serialized contest option."""

    option_id: str
    required_support: str
    title: str
    description: str


class ParticipantJson(TypedDict):
    """JSON shape for one serialized contest participant."""

    participant_id: str
    name: str
    weight: str


class BallotJson(TypedDict):
    """JSON shape for one serialized contest ballot."""

    participant_id: str
    ranking: list[str]


class ContestDataJson(TypedDict):
    """JSON shape for serialized immutable contest input data."""

    options: list[OptionJson]
    participants: list[ParticipantJson]
    ballots: list[BallotJson]


class CountEventJson(TypedDict):
    """JSON shape for one serialized audit-log event."""

    step_index: int
    phase_type: str
    phase_index: int
    round_number: int | None
    iteration_number: int | None
    event_type: str
    message: str
    option_id: str | None
    participant_id: str | None
    details: dict[str, object]


class CountSnapshotJson(TypedDict):
    """JSON shape for one serialized tally snapshot."""

    step_index: int
    phase_type: str
    phase_index: int
    round_number: int | None
    iteration_number: int | None
    tallies: dict[str, str]
    thresholds: dict[str, str]
    statuses: dict[str, str]
    exhausted_value: str


class ContestResultJson(TypedDict):
    """JSON shape for a serialized counted contest result."""

    selected_option_ids: list[str]
    audit_log: list[CountEventJson]
    snapshots: list[CountSnapshotJson]


def serialize_contest_data(data: ContestData) -> ContestDataJson:
    """Return a JSON-friendly dictionary for immutable contest input data."""
    return data.model_dump(mode="json")


def serialize_contest_result(result: ContestResult) -> ContestResultJson:
    """Return a JSON-friendly dictionary for a counted contest result."""
    audit_log: list[CountEventJson] = [
        _serialize_count_event(event) for event in result.audit_log
    ]
    snapshots: list[CountSnapshotJson] = [
        _serialize_count_snapshot(snapshot) for snapshot in result.snapshots
    ]
    return {
        "selected_option_ids": list(result.selected_option_ids),
        "audit_log": audit_log,
        "snapshots": snapshots,
    }


def _serialize_count_event(event: CountEvent) -> CountEventJson:
    """Return a typed JSON representation of one audit-log event."""
    return {
        "step_index": event.step_index,
        "phase_type": event.phase_type.value,
        "phase_index": event.phase_index,
        "round_number": event.round_number,
        "iteration_number": event.iteration_number,
        "event_type": event.event_type,
        "message": event.message,
        "option_id": event.option_id,
        "participant_id": event.participant_id,
        "details": dict(event.details),
    }


def _serialize_count_snapshot(snapshot: RoundSnapshot) -> CountSnapshotJson:
    """Return a typed JSON representation of one tally snapshot."""
    return {
        "step_index": snapshot.step_index,
        "phase_type": snapshot.phase_type.value,
        "phase_index": snapshot.phase_index,
        "round_number": snapshot.round_number,
        "iteration_number": snapshot.iteration_number,
        "tallies": {
            option_id: _decimal_to_string(value)
            for option_id, value in snapshot.tallies.items()
        },
        "thresholds": {
            option_id: _decimal_to_string(value)
            for option_id, value in snapshot.thresholds.items()
        },
        "statuses": {
            option_id: snapshot.statuses[option_id].value
            for option_id in snapshot.statuses
        },
        "exhausted_value": _decimal_to_string(snapshot.exhausted_value),
    }


def _decimal_to_string(value: Decimal) -> str:
    """Return a stable string representation for Decimal values in JSON output."""
    return format(value, "f")
