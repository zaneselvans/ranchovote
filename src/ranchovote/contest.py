"""High-level orchestration for running one configured contest count.

This module intentionally stays thin. It binds validated input data to a selected
counting method and delegates the actual counting work to that method. Keeping this
layer small makes it easier to experiment with different STV variants without mixing
algorithm details into application entry points.
"""

from dataclasses import dataclass

from ranchovote.methods.base import CountingMethod
from ranchovote.models import ContestData
from ranchovote.trace import ContestResult


@dataclass(slots=True)
class Contest:
    """Run a configured counting method against validated contest input data."""

    data: ContestData
    counting_method: CountingMethod

    def run(self) -> ContestResult:
        """Execute the configured counting method."""
        return self.counting_method.run(data=self.data)
