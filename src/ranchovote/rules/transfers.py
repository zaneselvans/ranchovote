"""Rules for redistributing surplus support after options are selected.

Surplus handling is one of the most method-specific parts of STV. By isolating it in
its own module, ranchovote can compare transfer policies without tangling them up with
ballot allocation, selection, or persistence concerns.
"""

from abc import ABC, abstractmethod
from collections.abc import Mapping, Sequence
from decimal import Decimal

from ranchovote.models import ContestData, OptionId
from ranchovote.state import ContestState


class SurplusTransferRule(ABC):
    """Adjust state after one or more options are selected in round-based STV."""

    @abstractmethod
    def apply_surplus_transfers(
        self,
        *,
        selected_option_ids: Sequence[OptionId],
        data: ContestData,
        state: ContestState,
        thresholds: Mapping[OptionId, Decimal],
    ) -> None:
        """Mutate state to reflect surplus transfers after selection."""


class InclusiveGregorySurplusTransferRule(SurplusTransferRule):
    """Placeholder for the first concrete deterministic surplus transfer rule.

    This rule family is chosen because it matches the intuitive round-based STV story
    that is easiest to explain to users, while still having a canonical name in the
    literature.
    """

    def apply_surplus_transfers(
        self,
        *,
        selected_option_ids: Sequence[OptionId],
        data: ContestData,
        state: ContestState,
        thresholds: Mapping[OptionId, Decimal],
    ) -> None:
        """Apply fractional surplus transfers after one or more selections."""
        # This rule only mutates already-validated state, so dropping the unused
        # input makes that explicit and prevents the placeholder signature from
        # implying that transfer logic still consults raw contest data here.
        del data
        for option_id in selected_option_ids:
            threshold, current_tally = self._option_transfer_inputs(
                option_id=option_id,
                state=state,
                thresholds=thresholds,
            )
            keep_factor = self._keep_factor(
                current_tally=current_tally,
                threshold=threshold,
            )
            state.keep_factors[option_id] = keep_factor
            if current_tally <= 0:
                continue

            self._update_ballot_weights(
                keep_factor=keep_factor,
                option_id=option_id,
                state=state,
            )
            self._record_surplus_event(
                current_tally=current_tally,
                keep_factor=keep_factor,
                option_id=option_id,
                state=state,
                threshold=threshold,
            )

    def _option_transfer_inputs(
        self,
        *,
        option_id: OptionId,
        state: ContestState,
        thresholds: Mapping[OptionId, Decimal],
    ) -> tuple[Decimal, Decimal]:
        """Return validated threshold and tally values for one selected option."""
        if option_id not in thresholds:
            msg = f"Missing threshold for option_id: {option_id}"
            raise ValueError(msg)
        if option_id not in state.tallies:
            msg = f"Missing tally for option_id: {option_id}"
            raise ValueError(msg)
        return thresholds[option_id], state.tallies[option_id]

    def _keep_factor(
        self,
        *,
        current_tally: Decimal,
        threshold: Decimal,
    ) -> Decimal:
        """Return the Inclusive Gregory keep factor for a selected option."""
        if current_tally <= 0:
            return Decimal(0)

        keep_factor = threshold / current_tally
        if keep_factor > Decimal(1):
            return Decimal(1)
        if keep_factor < Decimal(0):
            return Decimal(0)
        return keep_factor

    def _update_ballot_weights(
        self,
        *,
        keep_factor: Decimal,
        option_id: OptionId,
        state: ContestState,
    ) -> None:
        """Reduce ballot weights so only the surplus remains transferable."""
        for participant_id, allocations in state.ballot_allocations.items():
            if option_id not in allocations:
                continue
            if participant_id not in state.ballot_weights:
                msg = f"Missing ballot weight for participant_id: {participant_id}"
                raise ValueError(msg)

            allocated_value = allocations[option_id]
            if allocated_value < 0:
                msg = f"Allocated value must be non-negative for option_id: {option_id}"
                raise ValueError(msg)

            updated_weight = state.ballot_weights[participant_id] - (
                allocated_value * keep_factor
            )
            if updated_weight < 0:
                msg = (
                    "Updated ballot weight became negative after surplus transfer for "
                    f"participant_id: {participant_id}"
                )
                raise ValueError(msg)
            state.ballot_weights[participant_id] = updated_weight

    def _record_surplus_event(
        self,
        *,
        current_tally: Decimal,
        keep_factor: Decimal,
        option_id: OptionId,
        state: ContestState,
        threshold: Decimal,
    ) -> None:
        """Record the trace event for one Inclusive Gregory surplus transfer."""
        surplus_value = current_tally - threshold
        if surplus_value < 0:
            surplus_value = Decimal(0)

        state.record_event(
            event_type="surplus-transfer",
            message=f"Applied Inclusive Gregory surplus transfer for {option_id}.",
            option_id=option_id,
            details={
                "tally": format(current_tally, "f"),
                "threshold": format(threshold, "f"),
                "surplus": format(surplus_value, "f"),
                "keep_factor": format(keep_factor, "f"),
            },
        )
