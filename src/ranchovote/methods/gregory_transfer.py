"""Gregory-transfer round-based counting method presets and implementation.

This module implements a reusable Gregory-transfer STV family. The canonical
Inclusive Gregory label is reserved for narrower presets whose overall behavior is
close enough to outside expectations to justify the literature-facing name.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal
from typing import Self

from ranchovote.methods.base import RoundBasedCountingMethod
from ranchovote.models import Ballot, ContestData, OptionId
from ranchovote.rules.allocation import FirstActivePreferenceAllocationRule
from ranchovote.rules.exclusion import (
    InputOrderTieBreakRule,
    LowestTallyExclusionRule,
)
from ranchovote.rules.selection import ThresholdSelectionRule
from ranchovote.rules.thresholds import (
    ConstantThresholdRule,
    OptionThresholdMapRule,
    ThresholdRule,
)
from ranchovote.rules.transfers import InclusiveGregorySurplusTransferRule
from ranchovote.state import ContestState, OptionStatus
from ranchovote.trace import ContestResult


@dataclass(slots=True)
class InclusiveGregoryCountingMethod(RoundBasedCountingMethod):
    """Concrete Gregory-transfer round-based STV implementation.

    The stable family identity of this implementation is Gregory-transfer STV. Some
    presets, such as the uniform-threshold constructor, may be described publicly as
    Inclusive Gregory. More experimental threshold configurations remain in the same
    family while using a more descriptive non-canonical public label.
    """

    @classmethod
    def with_threshold_rule(cls, *, threshold_rule: ThresholdRule) -> Self:
        """Return Gregory-transfer STV with an explicit custom threshold rule.

        This is the most general constructor. It intentionally uses a family-level
        descriptive label rather than the narrower Inclusive Gregory literature name.
        """
        return cls(
            threshold_rule=threshold_rule,
            ballot_allocation_rule=FirstActivePreferenceAllocationRule(),
            selection_rule=ThresholdSelectionRule(),
            surplus_transfer_rule=InclusiveGregorySurplusTransferRule(),
            exclusion_rule=LowestTallyExclusionRule(),
            tie_break_rule=InputOrderTieBreakRule(),
            family_id="gregory-transfer-stv",
            method_name="gregory-transfer-stv (custom threshold rule)",
        )

    @classmethod
    def with_uniform_threshold(cls, *, threshold: Decimal) -> Self:
        """Return the canonical Inclusive Gregory preset with one threshold.

        Use this for classical STV-style examples or other contests in which every
        option is evaluated against the same selection target.
        """
        return cls(
            threshold_rule=ConstantThresholdRule(threshold=threshold),
            ballot_allocation_rule=FirstActivePreferenceAllocationRule(),
            selection_rule=ThresholdSelectionRule(),
            surplus_transfer_rule=InclusiveGregorySurplusTransferRule(),
            exclusion_rule=LowestTallyExclusionRule(),
            tie_break_rule=InputOrderTieBreakRule(),
            family_id="gregory-transfer-stv",
            method_name="inclusive-gregory",
        )

    @classmethod
    def with_option_thresholds(
        cls,
        *,
        thresholds_by_option: Mapping[OptionId, Decimal],
    ) -> Self:
        """Return Gregory-transfer STV using explicit thresholds for each option.

        This remains in the same Gregory-transfer family, but uses a descriptive
        non-canonical label because the threshold configuration is more specialized.
        """
        return cls(
            threshold_rule=OptionThresholdMapRule(
                thresholds_by_option=thresholds_by_option
            ),
            ballot_allocation_rule=FirstActivePreferenceAllocationRule(),
            selection_rule=ThresholdSelectionRule(),
            surplus_transfer_rule=InclusiveGregorySurplusTransferRule(),
            exclusion_rule=LowestTallyExclusionRule(),
            tie_break_rule=InputOrderTieBreakRule(),
            family_id="gregory-transfer-stv",
            method_name="gregory-transfer-stv (per-option thresholds)",
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

            excluded_option_id = self.exclusion_rule.exclude_option(
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
