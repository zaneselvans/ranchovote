"""Textual application factories for browsing persisted contest traces.

This module provides a lightweight terminal explorer over the same read-side service
used by the FastAPI app. The intent is to let users inspect stored runs locally from a
terminal without duplicating query logic in a second interface-specific stack.
"""

from pathlib import Path
from typing import ClassVar

from textual.app import App, ComposeResult
from textual.widgets import DataTable, Footer, Header, Static

from ranchovote.services.traces import TraceService
from ranchovote.storage.duckdb import DuckDbTraceStore


def create_trace_tui(*, trace_service: TraceService) -> App[None]:
    """Create a Textual app backed by the shared trace-query service."""
    service = trace_service

    class TraceExplorerApp(App[None]):
        """Minimal Textual shell for browsing persisted contest runs."""

        BINDINGS: ClassVar[list[tuple[str, str, str]]] = [
            ("q", "quit", "Quit"),
            ("r", "refresh", "Refresh"),
        ]

        def compose(self) -> ComposeResult:
            """Compose the primary widgets for the trace explorer."""
            yield Header()
            yield Static("Persisted contest runs", id="run-summary")
            yield DataTable(id="runs-table")
            yield Footer()

        def on_mount(self) -> None:
            """Load the initial set of persisted runs when the app starts."""
            self._refresh_runs()

        def action_refresh(self) -> None:
            """Reload the persisted run list from the shared trace service."""
            self._refresh_runs()

        def _refresh_runs(self) -> None:
            """Populate the run table from the shared read-side service."""
            run_summaries = service.list_runs()
            table = self.query_one("#runs-table", DataTable)
            table.clear(columns=True)
            table.add_columns(
                "run_id",
                "created_at",
                "method",
                "selected_options",
                "events",
                "snapshots",
            )
            for run_summary in run_summaries:
                table.add_row(
                    str(run_summary.run_id),
                    run_summary.created_at.isoformat(sep=" ", timespec="seconds"),
                    run_summary.method_name,
                    ", ".join(run_summary.selected_option_ids),
                    str(run_summary.event_count),
                    str(run_summary.snapshot_count),
                )

            summary = self.query_one("#run-summary", Static)
            summary.update(f"Persisted contest runs: {len(run_summaries)}")

    return TraceExplorerApp()


def create_default_trace_tui(*, database_path: Path) -> App[None]:
    """Create a Textual app using the DuckDB-backed shared trace service."""
    trace_store = DuckDbTraceStore(database_path=database_path)
    trace_service = TraceService(trace_repository=trace_store)
    return create_trace_tui(trace_service=trace_service)
