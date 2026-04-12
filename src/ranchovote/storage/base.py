"""Abstract interfaces for writing and reading persisted trace data.

These interfaces define the contract between the rest of the application and any
storage backend. Separating the abstract read and write responsibilities makes it
easier to evolve the persistence layer without rewriting services or interfaces.
"""

from abc import ABC, abstractmethod
from uuid import UUID

from ranchovote.models import ContestData
from ranchovote.trace import (
    ContestResult,
    PersistedContestRun,
    PersistedContestRunSummary,
)


class TraceStore(ABC):
    """Persist counted contest traces for later comparison and analysis."""

    @abstractmethod
    def write_result(
        self,
        *,
        contest_data: ContestData,
        method_name: str,
        result: ContestResult,
    ) -> None:
        """Persist one complete contest run and its trace."""


class TraceRepository(ABC):
    """Read persisted contest traces for shared API and TUI use cases."""

    @abstractmethod
    def list_runs(self) -> tuple[PersistedContestRunSummary, ...]:
        """Return persisted run summaries in display order."""

    @abstractmethod
    def get_run(self, *, run_id: UUID) -> PersistedContestRun | None:
        """Return one persisted contest run, or None when it does not exist."""
