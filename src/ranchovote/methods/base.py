"""Abstract foundations for contest counting methods.

The classes in this module define the common interface that orchestration code relies
on and the shared structure used by broad method families. They make it possible to add
new counting algorithms without changing the rest of the application architecture.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal

from ranchovote.models import ContestData
from ranchovote.rules.allocation import BallotAllocationRule
from ranchovote.rules.exclusion import ExclusionRule, TieBreakRule
from ranchovote.rules.selection import SelectionRule
from ranchovote.rules.thresholds import ThresholdRule
from ranchovote.rules.transfers import SurplusTransferRule
from ranchovote.state import ContestState
from ranchovote.trace import ContestResult


class CountingMethod(ABC):
    """Top-level interface for a complete contest counting method."""

    family_id: str
    """Stable family identifier for this counting method."""

    method_name: str
    """Human-readable name of the counting method."""

    @abstractmethod
    def initial_state(self, *, data: ContestData) -> ContestState:
        """Create the initial runtime state for a new contest run."""

    @abstractmethod
    def run(self, *, data: ContestData) -> ContestResult:
        """Execute the full contest and return the final result."""


@dataclass(slots=True)
class RoundBasedCountingMethod(CountingMethod, ABC):
    """Base class for discrete, round-based STV methods."""

    threshold_rule: ThresholdRule
    ballot_allocation_rule: BallotAllocationRule
    selection_rule: SelectionRule
    surplus_transfer_rule: SurplusTransferRule
    exclusion_rule: ExclusionRule
    tie_break_rule: TieBreakRule
    family_id: str = "round-based-stv"
    method_name: str = "round-based-stv"

    def initial_state(self, *, data: ContestData) -> ContestState:
        """Build the default initial state for a round-based count."""
        return ContestState.from_data(data)


@dataclass(slots=True)
class IterativeCountingMethod(CountingMethod, ABC):
    """Base class for iterative STV methods such as Meek or Warren variants."""

    threshold_rule: ThresholdRule
    ballot_allocation_rule: BallotAllocationRule
    selection_rule: SelectionRule
    tie_break_rule: TieBreakRule
    convergence_tolerance: Decimal
    max_iterations: int
    family_id: str = "iterative-stv"
    method_name: str = "iterative-stv"

    def initial_state(self, *, data: ContestData) -> ContestState:
        """Build the default initial state for an iterative count."""
        return ContestState.from_data(data)
