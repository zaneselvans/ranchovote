"""Placeholder container for a future Meek-style iterative counting method.

This module exists to reserve the architectural shape for iterative STV methods, which
behave differently from round-based methods because they repeatedly adjust keep factors
until they converge. The implementation is intentionally deferred, but the module makes
that future direction visible in the public API and documentation.
"""

from dataclasses import dataclass

from ranchovote.methods.base import IterativeCountingMethod
from ranchovote.models import ContestData
from ranchovote.trace import ContestResult


@dataclass(slots=True)
class MeekCountingMethod(IterativeCountingMethod):
    """Dedicated container for Meek-style iterative counting."""

    def run(self, *, data: ContestData) -> ContestResult:
        """Run the Meek count using iterative keep-factor updates."""
        msg = "MeekCountingMethod.run() is not implemented yet."
        raise NotImplementedError(msg)
