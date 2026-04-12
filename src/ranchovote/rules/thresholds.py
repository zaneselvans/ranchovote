"""Rules for determining the support required to select an option.

In ranchovote, thresholds generalize the idea of an STV quota. Some methods may use an
option-specific threshold supplied by contest configuration, while others may use a
single contest-wide threshold or derive a more dynamic threshold from the current
state of the count. This module isolates that choice.
"""

from abc import ABC, abstractmethod
from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal

from ranchovote.models import ContestData, Option, OptionId
from ranchovote.state import ContestState


class ThresholdRule(ABC):
    """Determine the support an option must reach to be selected.

    Threshold rules keep selection-support logic outside the core contest input
    models. Different contests may use a uniform threshold, explicit per-option
    thresholds, or later a derived quota formula, while still sharing the same
    validated `ContestData`.
    """

    @abstractmethod
    def threshold_for(
        self,
        *,
        option: Option,
        data: ContestData,
        state: ContestState,
    ) -> Decimal:
        """Return the current threshold for an option."""


@dataclass(slots=True, frozen=True)
class ConstantThresholdRule(ThresholdRule):
    """Use one contest-wide threshold for every option.

    This is the simplest configuration for classical STV-like examples where every
    option is selected against the same support target.
    """

    threshold: Decimal

    def __post_init__(self) -> None:
        """Validate the configured threshold value."""
        if self.threshold <= 0:
            msg = "ConstantThresholdRule.threshold must be greater than zero."
            raise ValueError(msg)

    def threshold_for(
        self,
        *,
        option: Option,
        data: ContestData,
        state: ContestState,
    ) -> Decimal:
        """Return the same fixed threshold for each option in the contest."""
        del option
        del data
        del state
        return self.threshold


@dataclass(slots=True, frozen=True)
class OptionThresholdMapRule(ThresholdRule):
    """Use an explicit contest-level threshold mapping keyed by option ID.

    This rule is useful when options legitimately have different support targets,
    such as in resource-allocation contests where options may require different
    amounts of support to succeed.
    """

    thresholds_by_option: Mapping[OptionId, Decimal]

    def __post_init__(self) -> None:
        """Validate that every configured threshold is positive."""
        if not self.thresholds_by_option:
            msg = "OptionThresholdMapRule.thresholds_by_option must not be empty."
            raise ValueError(msg)

        for option_id, threshold in self.thresholds_by_option.items():
            if threshold <= 0:
                msg = (
                    "OptionThresholdMapRule thresholds must be greater than zero for "
                    f"option_id: {option_id}"
                )
                raise ValueError(msg)

    def threshold_for(
        self,
        *,
        option: Option,
        data: ContestData,
        state: ContestState,
    ) -> Decimal:
        """Return the configured threshold for one option ID."""
        del data
        del state
        if option.option_id not in self.thresholds_by_option:
            msg = f"Missing configured threshold for option_id: {option.option_id}"
            raise ValueError(msg)
        return self.thresholds_by_option[option.option_id]
