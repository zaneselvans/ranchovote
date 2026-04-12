"""Rules for option exclusion order and deterministic tie breaking.

When no option can be selected in the current step, round-based methods need a policy
for choosing what to exclude next. This module keeps that policy separate from the
rest of the count so the choice can be documented, tested, and replaced explicitly.
"""

from abc import ABC, abstractmethod
from collections.abc import Mapping, Sequence
from decimal import Decimal

from ranchovote.models import ContestData, OptionId
from ranchovote.state import ContestState, OptionStatus


class TieBreakRule(ABC):
    """Resolve ties between options with otherwise equivalent standing."""

    @abstractmethod
    def break_tie(
        self,
        *,
        option_ids: Sequence[OptionId],
        data: ContestData,
        state: ContestState,
        reason: str,
    ) -> OptionId:
        """Return the chosen option ID for the tie-breaking situation."""


class EliminationRule(ABC):
    """Determine which option should be excluded when no option is selected."""

    @abstractmethod
    def exclude_option(
        self,
        *,
        data: ContestData,
        state: ContestState,
        thresholds: Mapping[OptionId, Decimal],
        tie_break_rule: TieBreakRule,
    ) -> OptionId:
        """Return the active option ID that should be excluded next."""


class InputOrderTieBreakRule(TieBreakRule):
    """Break ties deterministically using the option order from the input data."""

    def break_tie(
        self,
        *,
        option_ids: Sequence[OptionId],
        data: ContestData,
        state: ContestState,
        reason: str,
    ) -> OptionId:
        """Return the first tied option encountered in the input option order."""
        del state
        del reason
        tied_option_ids = set(option_ids)
        for option in data.options:
            if option.option_id in tied_option_ids:
                return option.option_id
        msg = "Tie-break options must all appear in contest input data."
        raise ValueError(msg)


class LowestTallyEliminationRule(EliminationRule):
    """Exclude the active option with the lowest current tally."""

    def exclude_option(
        self,
        *,
        data: ContestData,
        state: ContestState,
        thresholds: Mapping[OptionId, Decimal],
        tie_break_rule: TieBreakRule,
    ) -> OptionId:
        """Return the lowest-ranked active option under the current tally state."""
        del thresholds
        active_option_ids = [
            option.option_id
            for option in data.options
            if state.statuses.get(option.option_id) == OptionStatus.ACTIVE
        ]
        if not active_option_ids:
            msg = "Cannot eliminate an option when no active options remain."
            raise ValueError(msg)

        lowest_tally = min(
            state.tallies.get(option_id, Decimal(0)) for option_id in active_option_ids
        )
        tied_option_ids = [
            option_id
            for option_id in active_option_ids
            if state.tallies.get(option_id, Decimal(0)) == lowest_tally
        ]
        if len(tied_option_ids) == 1:
            return tied_option_ids[0]

        return tie_break_rule.break_tie(
            option_ids=tied_option_ids,
            data=data,
            state=state,
            reason="lowest-tally-exclusion",
        )
