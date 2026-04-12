"""Rules for deciding which options become selected from current tallies.

Selection rules translate the current tally state into contest outcomes. They are kept
separate from threshold computation and surplus handling so each conceptual decision in
the count remains visible and independently testable.
"""

from abc import ABC, abstractmethod
from collections.abc import Mapping
from decimal import Decimal

from ranchovote.models import ContestData, OptionId
from ranchovote.state import ContestState, OptionStatus


class SelectionRule(ABC):
    """Determine which active options are selected from the current tallies."""

    @abstractmethod
    def select_options(
        self,
        *,
        data: ContestData,
        state: ContestState,
        thresholds: Mapping[OptionId, Decimal],
    ) -> tuple[OptionId, ...]:
        """Return active option IDs that should become selected now."""


class ThresholdSelectionRule(SelectionRule):
    """Select any active option whose tally meets or exceeds its threshold."""

    def select_options(
        self,
        *,
        data: ContestData,
        state: ContestState,
        thresholds: Mapping[OptionId, Decimal],
    ) -> tuple[OptionId, ...]:
        """Return active options that currently satisfy their thresholds."""
        selected_option_ids: list[OptionId] = []

        for option in data.options:
            if option.option_id not in state.statuses:
                msg = f"Missing option status for option_id: {option.option_id}"
                raise ValueError(msg)
            if option.option_id not in thresholds:
                msg = f"Missing threshold for option_id: {option.option_id}"
                raise ValueError(msg)

            if state.statuses[option.option_id] != OptionStatus.ACTIVE:
                continue

            current_tally = state.tallies.get(option.option_id, Decimal(0))
            if current_tally >= thresholds[option.option_id]:
                selected_option_ids.append(option.option_id)

        return tuple(selected_option_ids)
