"""Rules for determining the support required to select an option.

In ranchovote, thresholds generalize the idea of an STV quota. Some methods may use an
option's required support directly, while others may derive a more dynamic threshold
from the current state of the count. This module isolates that choice.
"""

from abc import ABC, abstractmethod
from decimal import Decimal

from ranchovote.models import ContestData, Option
from ranchovote.state import ContestState


class ThresholdRule(ABC):
    """Determine the support an option must reach to be selected."""

    @abstractmethod
    def threshold_for(
        self,
        *,
        option: Option,
        data: ContestData,
        state: ContestState,
    ) -> Decimal:
        """Return the current threshold for an option."""


class RequiredSupportThresholdRule(ThresholdRule):
    """Use each option's required support as its selection threshold."""

    def threshold_for(
        self,
        *,
        option: Option,
        data: ContestData,
        state: ContestState,
    ) -> Decimal:
        """Return the fixed threshold implied by the option's required support."""
        del data
        del state
        return option.required_support
