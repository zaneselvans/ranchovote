"""Rules for mapping ballot value onto currently eligible options.

Allocation rules answer the question of where each participant's current voting value
should go at a given moment in the count. Different STV families make different
choices here, so the logic is isolated behind a small interface.
"""

from abc import ABC, abstractmethod
from collections.abc import Mapping
from decimal import Decimal

from ranchovote.models import Ballot, ContestData, OptionId
from ranchovote.state import ContestState, OptionStatus


class BallotAllocationRule(ABC):
    """Allocate each ballot's value across the currently eligible options."""

    @abstractmethod
    def allocation_for_ballot(
        self,
        *,
        ballot: Ballot,
        data: ContestData,
        state: ContestState,
    ) -> Mapping[OptionId, Decimal]:
        """Return the current allocation of ballot value across options."""


class FirstActivePreferenceAllocationRule(BallotAllocationRule):
    """Allocate each ballot to its first currently active ranked option."""

    def allocation_for_ballot(
        self,
        *,
        ballot: Ballot,
        data: ContestData,
        state: ContestState,
    ) -> Mapping[OptionId, Decimal]:
        """Return a single-project allocation for the first active preference."""
        del data
        if ballot.participant_id not in state.ballot_weights:
            msg = f"Missing ballot weight for participant_id: {ballot.participant_id}"
            raise ValueError(msg)

        ballot_weight = state.ballot_weights[ballot.participant_id]
        for option_id in ballot.ranking:
            if option_id not in state.statuses:
                msg = f"Missing option status for option_id: {option_id}"
                raise ValueError(msg)

            if state.statuses[option_id] == OptionStatus.ACTIVE:
                return {option_id: ballot_weight}
        return {}
