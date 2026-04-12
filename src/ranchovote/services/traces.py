"""Shared read-side service for exploring persisted contest traces.

This module provides a narrow application-facing API for listing and retrieving stored
contest runs. It keeps interface code focused on presentation while the repository and
storage layers remain responsible for persistence details.
"""

from dataclasses import dataclass
from uuid import UUID

from ranchovote.storage.base import TraceRepository
from ranchovote.trace import PersistedContestRun, PersistedContestRunSummary


@dataclass(slots=True)
class TraceService:
    """Provide one shared read model for FastAPI, Textual, and future interfaces."""

    trace_repository: TraceRepository

    def list_runs(self) -> tuple[PersistedContestRunSummary, ...]:
        """Return persisted runs in display order for UI clients."""
        return self.trace_repository.list_runs()

    def get_run(self, *, run_id: UUID) -> PersistedContestRun | None:
        """Return one persisted run for API or TUI detail views."""
        return self.trace_repository.get_run(run_id=run_id)
