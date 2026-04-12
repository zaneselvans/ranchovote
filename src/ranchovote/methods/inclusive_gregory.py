"""Inclusive Gregory counting method for the first concrete ranchovote variant.

Inclusive Gregory is a useful first implementation because it follows the classic STV
story of tallying, selecting, transferring surplus, and excluding. That makes it much
easier to explain than iterative methods, while still exercising the same state,
tracing, persistence, and rule-composition architecture that later methods will use.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Self

from ranchovote.methods.base import RoundBasedCountingMethod
from ranchovote.models import Ballot, ContestData, OptionId
from ranchovote.rules.allocation import FirstActivePreferenceAllocationRule
from ranchovote.rules.elimination import (
    InputOrderTieBreakRule,
    LowestTallyEliminationRule,
)
from ranchovote.rules.selection import ThresholdSelectionRule
from ranchovote.rules.thresholds import RequiredSupportThresholdRule
from ranchovote.rules.transfers import InclusiveGregorySurplusTransferRule
from ranchovote.state import ContestState, OptionStatus
from ranchovote.trace import ContestResult


@dataclass(slots=True)
class InclusiveGregoryCountingMethod(RoundBasedCountingMethod):
    """Concrete round-based STV method using Inclusive Gregory transfers."""

    @classmethod
    def configured(cls) -> Self:
        """Return the default Inclusive Gregory rule bundle for ranchovote."""
        return cls(
            threshold_rule=RequiredSupportThresholdRule(),
            ballot_allocation_rule=FirstActivePreferenceAllocationRule(),
            selection_rule=ThresholdSelectionRule(),
            surplus_transfer_rule=InclusiveGregorySurplusTransferRule(),
            elimination_rule=LowestTallyEliminationRule(),
            tie_break_rule=InputOrderTieBreakRule(),
            method_name="inclusive-gregory",
        )

    def run(self, *, data: ContestData) -> ContestResult:
        """Run the Inclusive Gregory count to completion."""
        state = self.initial_state(data=data)

        while state.active_option_ids():
            state.round_number += 1
            self._retally_ballots(data=data, state=state)
            thresholds = self._compute_thresholds(data=data, state=state)
            state.capture_snapshot(thresholds)
            state.record_event(
                event_type="round-tallied",
                message=f"Tallied votes for round {state.round_number}.",
                details={
                    "active_options": str(len(state.active_option_ids())),
                    "exhausted_value": format(state.exhausted_value, "f"),
                },
            )

            selected_option_ids = self.selection_rule.select_options(
                data=data,
                state=state,
                thresholds=thresholds,
            )
            if selected_option_ids:
                self._select_options(
                    selected_option_ids=selected_option_ids,
                    data=data,
                    state=state,
                    thresholds=thresholds,
                )
                self.surplus_transfer_rule.apply_surplus_transfers(
                    selected_option_ids=selected_option_ids,
                    data=data,
                    state=state,
                    thresholds=thresholds,
                )
                continue

            excluded_option_id = self.elimination_rule.exclude_option(
                data=data,
                state=state,
                thresholds=thresholds,
                tie_break_rule=self.tie_break_rule,
            )
            state.statuses[excluded_option_id] = OptionStatus.EXCLUDED
            state.keep_factors[excluded_option_id] = Decimal(0)
            state.record_event(
                event_type="option-excluded",
                message=f"Excluded option {excluded_option_id}.",
                option_id=excluded_option_id,
                details={
                    "tally": format(state.tallies[excluded_option_id], "f"),
                },
            )

        return ContestResult(
            selected_option_ids=state.selected_option_ids(),
            final_state=state,
            audit_log=tuple(state.audit_log),
            snapshots=tuple(state.snapshots),
        )

    def _compute_thresholds(
        self,
        *,
        data: ContestData,
        state: ContestState,
    ) -> dict[OptionId, Decimal]:
        """Return the current threshold for each option in the contest."""
        return {
            option.option_id: self.threshold_rule.threshold_for(
                option=option,
                data=data,
                state=state,
            )
            for option in data.options
        }

    def _select_options(
        self,
        *,
        selected_option_ids: tuple[OptionId, ...],
        data: ContestData,
        state: ContestState,
        thresholds: dict[OptionId, Decimal],
    ) -> None:
        """Mark the selected options and record trace events."""
        del data
        for option_id in selected_option_ids:
            if state.statuses.get(option_id) != OptionStatus.ACTIVE:
                continue
            if option_id not in thresholds:
                msg = f"Missing threshold for option_id: {option_id}"
                raise ValueError(msg)
            state.statuses[option_id] = OptionStatus.SELECTED
            state.record_event(
                event_type="option-selected",
                message=f"Selected option {option_id}.",
                option_id=option_id,
                details={
                    "tally": format(state.tallies[option_id], "f"),
                    "threshold": format(thresholds[option_id], "f"),
                },
            )

    def _retally_ballots(self, *, data: ContestData, state: ContestState) -> None:
        """Recompute ballot allocations, option tallies, and exhausted value."""
        state.tallies = {option.option_id: Decimal(0) for option in data.options}
        state.ballot_allocations = {}
        state.exhausted_value = Decimal(0)

        for ballot in data.ballots:
            self._allocate_ballot(ballot=ballot, data=data, state=state)

    def _allocate_ballot(
        self,
        *,
        ballot: Ballot,
        data: ContestData,
        state: ContestState,
    ) -> None:
        """Apply the ballot allocation rule to one ballot and update tallies."""
        if ballot.participant_id not in state.ballot_weights:
            msg = f"Missing ballot weight for participant_id: {ballot.participant_id}"
            raise ValueError(msg)

        allocation = dict(
            self.ballot_allocation_rule.allocation_for_ballot(
                ballot=ballot,
                data=data,
                state=state,
            )
        )
        state.ballot_allocations[ballot.participant_id] = allocation

        ballot_weight = state.ballot_weights[ballot.participant_id]
        allocated_total = Decimal(0)
        for option_id, allocation_value in allocation.items():
            if allocation_value < 0:
                msg = (
                    f"Ballot allocation must be non-negative for option_id: {option_id}"
                )
                raise ValueError(msg)
            if option_id not in state.tallies:
                msg = f"Missing tally bucket for option_id: {option_id}"
                raise ValueError(msg)

            allocated_total += allocation_value
            state.tallies[option_id] += allocation_value

        if allocated_total > ballot_weight:
            msg = (
                "Ballot allocation cannot exceed remaining ballot weight for "
                f"participant_id: {ballot.participant_id}"
            )
            raise ValueError(msg)

        state.exhausted_value += ballot_weight - allocated_total
