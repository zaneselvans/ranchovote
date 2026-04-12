"""Tests for DuckDB-backed trace persistence and retrieval."""

from decimal import Decimal
from pathlib import Path
from uuid import UUID

import duckdb

from ranchovote.methods.gregory_transfer import InclusiveGregoryCountingMethod
from ranchovote.models import Ballot, ContestData, Option, Participant
from ranchovote.storage.duckdb import DuckDbTraceStore


def test_duckdb_trace_store_persists_run_rows(tmp_path: Path) -> None:
    """A counted contest run can be written and read through the trace store."""
    contest_data = ContestData(
        options=(
            Option(
                option_id="solar",
                title="Solar",
                description="Fund rooftop solar.",
            ),
            Option(
                option_id="bikes",
                title="Bikes",
                description="Fund bike parking.",
            ),
        ),
        participants=(
            Participant(
                participant_id="alice",
                name="Alice",
                weight=Decimal(10),
            ),
            Participant(
                participant_id="bob",
                name="Bob",
                weight=Decimal(10),
            ),
        ),
        ballots=(
            Ballot(participant_id="alice", ranking=("solar", "bikes")),
            Ballot(participant_id="bob", ranking=("bikes", "solar")),
        ),
    )
    result = InclusiveGregoryCountingMethod.with_uniform_threshold(
        threshold=Decimal(10)
    ).run(data=contest_data)
    trace_store = DuckDbTraceStore(database_path=tmp_path / "trace.duckdb")

    trace_store.write_result(
        contest_data=contest_data,
        family_id="gregory-transfer-stv",
        method_name="inclusive-gregory",
        result=result,
    )

    connection = duckdb.connect(str(trace_store.database_path))
    try:
        run_count = connection.execute("SELECT COUNT(*) FROM contest_runs").fetchone()
        event_count = connection.execute(
            "SELECT COUNT(*) FROM contest_events"
        ).fetchone()
        snapshot_count = connection.execute(
            "SELECT COUNT(*) FROM contest_snapshots"
        ).fetchone()
    finally:
        connection.close()

    assert run_count is not None
    assert run_count[0] == 1
    assert event_count is not None
    assert event_count[0] > 0
    assert snapshot_count is not None
    assert snapshot_count[0] > 0

    run_summaries = trace_store.list_runs()

    assert len(run_summaries) == 1
    assert run_summaries[0].family_id == "gregory-transfer-stv"
    assert run_summaries[0].method_name == "inclusive-gregory"
    assert run_summaries[0].selected_option_ids == ("solar", "bikes")

    persisted_run = trace_store.get_run(run_id=UUID(str(run_summaries[0].run_id)))

    assert persisted_run is not None
    assert persisted_run.summary.run_id == run_summaries[0].run_id
    assert persisted_run.contest_data == contest_data
    assert len(persisted_run.audit_log) == len(result.audit_log)
    assert len(persisted_run.snapshots) == len(result.snapshots)
