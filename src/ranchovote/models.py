"""Validated, immutable input models for ranked collective-decision contests.

These models describe the problem definition for a contest run: which options are
eligible, who is participating, and how each participant ranked those options. They
use Pydantic so validation happens at the boundary, allowing the rest of the counting
code to assume the inputs are internally consistent.
"""

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator

OptionId = str
ParticipantId = str


class Option(BaseModel):
    """Immutable description of one option that may be selected."""

    model_config = ConfigDict(frozen=True)

    option_id: OptionId
    required_support: Decimal = Field(gt=0)
    title: str = Field(min_length=1, max_length=50)
    description: str = Field(min_length=1)


class Participant(BaseModel):
    """Immutable description of a participant and their available weight."""

    model_config = ConfigDict(frozen=True)

    participant_id: ParticipantId
    name: str = Field(min_length=1)
    weight: Decimal = Field(gt=0)


class Ballot(BaseModel):
    """Immutable ranked ballot submitted by a single participant."""

    model_config = ConfigDict(frozen=True)

    participant_id: ParticipantId
    ranking: tuple[OptionId, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_unique_rankings(self) -> Ballot:
        """Ensure a ballot does not rank the same option more than once."""
        unique_rankings = set(self.ranking)
        if len(unique_rankings) != len(self.ranking):
            msg = "Ballot rankings must not contain duplicate option IDs."
            raise ValueError(msg)
        return self


class ContestData(BaseModel):
    """Validated, immutable input data shared by all contest methods."""

    model_config = ConfigDict(frozen=True)

    options: tuple[Option, ...] = Field(min_length=1)
    participants: tuple[Participant, ...] = Field(min_length=1)
    ballots: tuple[Ballot, ...]

    @model_validator(mode="after")
    def validate_internal_consistency(self) -> ContestData:
        """Validate ID uniqueness and ballot references across the full contest."""
        option_ids = [option.option_id for option in self.options]
        participant_ids = [
            participant.participant_id for participant in self.participants
        ]

        if len(set(option_ids)) != len(option_ids):
            msg = "Option IDs must be unique within a contest."
            raise ValueError(msg)

        if len(set(participant_ids)) != len(participant_ids):
            msg = "Participant IDs must be unique within a contest."
            raise ValueError(msg)

        known_options = set(option_ids)
        known_participants = set(participant_ids)
        seen_ballots: set[ParticipantId] = set()

        for ballot in self.ballots:
            if ballot.participant_id not in known_participants:
                msg = (
                    "Ballot participant_id values must refer to participants present "
                    "in the contest."
                )
                raise ValueError(msg)

            if ballot.participant_id in seen_ballots:
                msg = "Each participant may submit at most one ballot per contest."
                raise ValueError(msg)
            seen_ballots.add(ballot.participant_id)

            unknown_options = [
                option_id
                for option_id in ballot.ranking
                if option_id not in known_options
            ]
            if unknown_options:
                unknown_option_list = ", ".join(unknown_options)
                msg = (
                    "Ballot rankings must only reference known option IDs. "
                    f"Unknown values: {unknown_option_list}"
                )
                raise ValueError(msg)

        return self

    def option_by_id(self, option_id: OptionId) -> Option:
        """Return an option by ID after contest validation has succeeded."""
        for option in self.options:
            if option.option_id == option_id:
                return option
        msg = f"Unknown option_id: {option_id}"
        raise KeyError(msg)

    def participant_by_id(self, participant_id: ParticipantId) -> Participant:
        """Return a participant by ID after contest validation has succeeded."""
        for participant in self.participants:
            if participant.participant_id == participant_id:
                return participant
        msg = f"Unknown participant_id: {participant_id}"
        raise KeyError(msg)
