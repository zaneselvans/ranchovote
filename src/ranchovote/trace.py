"""Structured audit models for counted contests.

The trace layer records what happened during a run in a machine-readable form that is
useful for debugging, user-facing explanations, persistence, and future visualizations.
It separates event and snapshot data from the live counting state so completed runs can
be inspected long after the algorithm has finished.

This module uses both dataclasses and Pydantic on purpose. Dataclasses are used for
the internal event, snapshot, and result records created during counting. Pydantic is
used for persisted run views that cross back into storage, API, or UI boundaries.
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from ranchovote.models import ContestData, OptionId, ParticipantId
from ranchovote.state import ContestState, OptionStatus


class TracePhaseType(StrEnum):
    """Method-agnostic phase labels for persisted trace records."""

    INITIAL = "initial"
    ROUND = "round"
    ITERATION = "iteration"
    FINAL = "final"


@dataclass(slots=True)
class CountEvent:
    """Structured audit event recorded during the contest count."""

    step_index: int
    phase_type: TracePhaseType
    phase_index: int
    round_number: int | None
    iteration_number: int | None
    event_type: str
    message: str
    option_id: OptionId | None = None
    participant_id: ParticipantId | None = None
    details: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class RoundSnapshot:
    """Observed state at the end of a counting round or iteration."""

    step_index: int
    phase_type: TracePhaseType
    phase_index: int
    round_number: int | None
    iteration_number: int | None
    tallies: dict[OptionId, Decimal]
    thresholds: dict[OptionId, Decimal]
    statuses: dict[OptionId, OptionStatus]
    exhausted_value: Decimal


@dataclass(slots=True, frozen=True)
class ContestResult:
    """Final result returned by a counting method."""

    selected_option_ids: tuple[OptionId, ...]
    final_state: ContestState
    audit_log: tuple[CountEvent, ...]
    snapshots: tuple[RoundSnapshot, ...]


class PersistedContestRunSummary(BaseModel):
    """Compact summary of one persisted contest run.

    This uses Pydantic because persisted summaries are reconstructed from storage and
    exposed to interface layers, so boundary-style validation and serialization are
    useful again here.
    """

    model_config = ConfigDict(frozen=True)

    run_id: UUID
    created_at: datetime
    family_id: str
    method_name: str
    selected_option_ids: tuple[OptionId, ...]
    event_count: int = Field(ge=0)
    snapshot_count: int = Field(ge=0)


class PersistedContestRun(BaseModel):
    """Fully hydrated persisted contest run for UI and API consumers.

    Unlike the low-level trace records, this model sits at a read boundary and is
    therefore represented as a Pydantic model.
    """

    model_config = ConfigDict(frozen=True)

    summary: PersistedContestRunSummary
    contest_data: ContestData
    audit_log: tuple[CountEvent, ...]
    snapshots: tuple[RoundSnapshot, ...]
