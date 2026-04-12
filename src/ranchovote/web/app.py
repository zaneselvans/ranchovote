"""FastAPI application factories for persisted contest-trace exploration.

This module defines a small HTTP interface over the shared trace service. It is kept
deliberately narrow for now so the storage-backed read model can stabilize before more
detailed browsing, filtering, or mutation endpoints are introduced.
"""

from pathlib import Path
from uuid import UUID

from fastapi import FastAPI, HTTPException

from ranchovote.services.traces import TraceService
from ranchovote.storage.duckdb import DuckDbTraceStore


def create_trace_api(*, trace_service: TraceService) -> FastAPI:
    """Create a FastAPI app backed by the shared trace-query service."""
    app = FastAPI(
        title="ranchovote trace explorer",
        summary="Explore persisted contest runs, events, and snapshots.",
    )

    @app.get("/health")
    def health() -> dict[str, str]:
        """Return a minimal liveness response."""
        return {"status": "ok"}

    @app.get("/runs")
    def list_runs() -> tuple[object, ...]:
        """Return persisted run summaries for list views."""
        return trace_service.list_runs()

    @app.get("/runs/{run_id}")
    def get_run(run_id: UUID) -> object:
        """Return one persisted run for detailed inspection."""
        run = trace_service.get_run(run_id=run_id)
        if run is None:
            raise HTTPException(status_code=404, detail="Contest run not found")
        return run

    return app


def create_default_trace_api(*, database_path: Path) -> FastAPI:
    """Create a FastAPI app using the DuckDB-backed shared trace service."""
    trace_store = DuckDbTraceStore(database_path=database_path)
    trace_service = TraceService(trace_repository=trace_store)
    return create_trace_api(trace_service=trace_service)
