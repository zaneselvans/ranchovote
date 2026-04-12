"""Mutable runtime state used while a counting method is executing.

Unlike the input models, this state changes from step to step as tallies are updated,
options are selected or excluded, and trace records are captured. The goal is to keep
all transient counting state in one place so methods and rules can cooperate without
mutating the immutable contest inputs.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
from decimal import Decimal
from enum import StrEnum
from typing import TYPE_CHECKING

from ranchovote.models import ContestData, OptionId, ParticipantId

if TYPE_CHECKING:
    from ranchovote.trace import CountEvent, RoundSnapshot, TracePhaseType


class OptionStatus(StrEnum):
    """Lifecycle state for an option during a contest count."""

    ACTIVE = "active"
    SELECTED = "selected"
    EXCLUDED = "excluded"


@dataclass(slots=True)
class ContestState:
    """Mutable state shared by concrete counting methods during a run."""

    step_index: int
    round_number: int
    iteration_number: int | None
    tallies: dict[OptionId, Decimal]
    statuses: dict[OptionId, OptionStatus]
    exhausted_value: Decimal
    ballot_weights: dict[ParticipantId, Decimal]
    ballot_allocations: dict[ParticipantId, dict[OptionId, Decimal]]
    keep_factors: dict[OptionId, Decimal]
    snapshots: list[RoundSnapshot] = field(default_factory=list)
    audit_log: list[CountEvent] = field(default_factory=list)

    @classmethod
    def from_data(cls, data: ContestData) -> ContestState:
        """Create a blank initial state for a new contest run."""
        tallies = {option.option_id: Decimal(0) for option in data.options}
        statuses = {option.option_id: OptionStatus.ACTIVE for option in data.options}
        ballot_weights = {
            participant.participant_id: participant.weight
            for participant in data.participants
        }
        keep_factors = {option.option_id: Decimal(1) for option in data.options}
        return cls(
            step_index=0,
            round_number=0,
            iteration_number=None,
            tallies=tallies,
            statuses=statuses,
            exhausted_value=Decimal(0),
            ballot_weights=ballot_weights,
            ballot_allocations={},
            keep_factors=keep_factors,
        )

    def active_option_ids(self) -> tuple[OptionId, ...]:
        """Return the currently active options in a stable order."""
        return tuple(
            option_id
            for option_id, status in self.statuses.items()
            if status == OptionStatus.ACTIVE
        )

    def selected_option_ids(self) -> tuple[OptionId, ...]:
        """Return options already selected in a stable order."""
        return tuple(
            option_id
            for option_id, status in self.statuses.items()
            if status == OptionStatus.SELECTED
        )

    def record_event(
        self,
        *,
        event_type: str,
        message: str,
        option_id: OptionId | None = None,
        participant_id: ParticipantId | None = None,
        details: Mapping[str, str] | None = None,
    ) -> None:
        """Append a structured audit event to the state log."""
        from ranchovote.trace import CountEvent

        step_index = self._next_step_index()
        phase_type, phase_index = self._phase_metadata()
        self.audit_log.append(
            CountEvent(
                step_index=step_index,
                phase_type=phase_type,
                phase_index=phase_index,
                round_number=self._round_number_for_trace(),
                iteration_number=self.iteration_number,
                event_type=event_type,
                message=message,
                option_id=option_id,
                participant_id=participant_id,
                details=dict(details or {}),
            )
        )

    def capture_snapshot(self, thresholds: Mapping[OptionId, Decimal]) -> None:
        """Persist a point-in-time summary for debugging and visualization."""
        from ranchovote.trace import RoundSnapshot

        step_index = self._next_step_index()
        phase_type, phase_index = self._phase_metadata()
        self.snapshots.append(
            RoundSnapshot(
                step_index=step_index,
                phase_type=phase_type,
                phase_index=phase_index,
                round_number=self._round_number_for_trace(),
                iteration_number=self.iteration_number,
                tallies=dict(self.tallies),
                thresholds=dict(thresholds),
                statuses=dict(self.statuses),
                exhausted_value=self.exhausted_value,
            )
        )

    def _next_step_index(self) -> int:
        """Advance and return the next persisted trace step index."""
        self.step_index += 1
        return self.step_index

    def _phase_metadata(self) -> tuple[TracePhaseType, int]:
        """Return generalized phase metadata for the current counting state."""
        from ranchovote.trace import TracePhaseType

        if self.iteration_number is not None:
            return TracePhaseType.ITERATION, self.iteration_number
        if self.round_number > 0:
            return TracePhaseType.ROUND, self.round_number
        return TracePhaseType.INITIAL, 0

    def _round_number_for_trace(self) -> int | None:
        """Return the round number when it is meaningful for this trace record."""
        if self.round_number <= 0:
            return None
        return self.round_number
