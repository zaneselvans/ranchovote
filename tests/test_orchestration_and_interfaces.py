"""Tests for contest orchestration, serialization, services, and web interfaces."""

import inspect
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from ranchovote.contest import Contest
from ranchovote.io.json import serialize_contest_data, serialize_contest_result
from ranchovote.methods.base import CountingMethod
from ranchovote.methods.gregory_transfer import InclusiveGregoryCountingMethod
from ranchovote.models import Ballot, ContestData, Option, Participant
from ranchovote.services.traces import TraceService
from ranchovote.state import ContestState
from ranchovote.storage.base import TraceRepository, TraceStore
from ranchovote.storage.schema import contest_runs_table
from ranchovote.trace import (
    ContestResult,
    PersistedContestRun,
    PersistedContestRunSummary,
)
from ranchovote.web.app import create_default_trace_api, create_trace_api


def build_contest_data() -> ContestData:
    """Return a valid contest fixture for orchestration and API tests."""
    return ContestData(
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


@dataclass(slots=True)
class StubCountingMethod(CountingMethod):
    """Minimal counting method used to test Contest delegation."""

    result: ContestResult
    family_id: str = "stub-family"
    method_name: str = "stub"

    def initial_state(self, *, data: ContestData) -> ContestState:
        """Return the standard initial state."""
        return ContestState.from_data(data)

    def run(self, *, data: ContestData) -> ContestResult:
        """Return the precomputed result passed into the stub."""
        del data
        return self.result


@dataclass(slots=True)
class FakeTraceRepository(TraceRepository):
    """Small in-memory repository used by service and API tests."""

    run: PersistedContestRun

    def list_runs(self) -> tuple[PersistedContestRunSummary, ...]:
        """Return the known run summary."""
        return (self.run.summary,)

    def get_run(self, *, run_id: UUID) -> PersistedContestRun | None:
        """Return the run only when the ID matches."""
        if run_id == self.run.summary.run_id:
            return self.run
        return None


def build_persisted_run() -> PersistedContestRun:
    """Return one persisted run object for API and service tests."""
    contest_data = build_contest_data()
    result = InclusiveGregoryCountingMethod.with_uniform_threshold(
        threshold=Decimal(10)
    ).run(data=contest_data)
    summary = PersistedContestRunSummary(
        run_id=uuid4(),
        created_at=datetime.now(),
        family_id="gregory-transfer-stv",
        method_name="inclusive-gregory",
        selected_option_ids=result.selected_option_ids,
        event_count=len(result.audit_log),
        snapshot_count=len(result.snapshots),
    )
    return PersistedContestRun(
        summary=summary,
        contest_data=contest_data,
        audit_log=result.audit_log,
        snapshots=result.snapshots,
    )


def test_contest_delegates_to_counting_method() -> None:
    """Contest should return the configured counting method's result."""
    data = build_contest_data()
    result = InclusiveGregoryCountingMethod.with_uniform_threshold(
        threshold=Decimal(10)
    ).run(data=data)
    contest = Contest(data=data, counting_method=StubCountingMethod(result=result))

    assert contest.run() == result


def test_json_serialization_covers_inputs_and_results() -> None:
    """JSON helpers should serialize both immutable input data and counted results."""
    data = build_contest_data()
    result = InclusiveGregoryCountingMethod.with_uniform_threshold(
        threshold=Decimal(10)
    ).run(data=data)

    serialized_data = serialize_contest_data(data)
    serialized_result = serialize_contest_result(result)

    assert serialized_data["options"][0]["option_id"] == "solar"
    assert "required_support" not in serialized_data["options"][0]
    assert serialized_result["selected_option_ids"] == ["solar", "bikes"]
    assert serialized_result["snapshots"][0]["tallies"]["solar"] == "10"
    assert serialized_result["snapshots"][0]["exhausted_value"] == "0"


def test_trace_service_delegates_to_repository() -> None:
    """TraceService should expose repository-backed run summaries and details."""
    persisted_run = build_persisted_run()
    service = TraceService(trace_repository=FakeTraceRepository(run=persisted_run))

    assert service.list_runs() == (persisted_run.summary,)
    assert service.get_run(run_id=persisted_run.summary.run_id) == persisted_run
    assert service.get_run(run_id=uuid4()) is None


def test_shared_naming_contract_stays_aligned_across_layers() -> None:
    """Shared identifiers should keep the same names across method, trace, and storage layers."""
    counting_method_fields = set(CountingMethod.__annotations__)
    persisted_summary_fields = set(PersistedContestRunSummary.model_fields)
    storage_columns = set(contest_runs_table.c.keys())
    trace_store_parameters = set(inspect.signature(TraceStore.write_result).parameters)

    expected_shared_names = {"family_id", "method_name"}
    legacy_names = {"family_name", "method_family", "name"}

    assert expected_shared_names <= counting_method_fields
    assert expected_shared_names <= persisted_summary_fields
    assert expected_shared_names <= storage_columns
    assert expected_shared_names <= trace_store_parameters

    assert legacy_names.isdisjoint(counting_method_fields)
    assert legacy_names.isdisjoint(persisted_summary_fields)
    assert legacy_names.isdisjoint(storage_columns)
    assert legacy_names.isdisjoint(trace_store_parameters)


def test_trace_api_exposes_health_run_list_and_run_detail() -> None:
    """The FastAPI app should expose all current trace explorer routes."""
    persisted_run = build_persisted_run()
    service = TraceService(trace_repository=FakeTraceRepository(run=persisted_run))
    client = TestClient(create_trace_api(trace_service=service))

    assert client.get("/health").json() == {"status": "ok"}

    run_list_response = client.get("/runs")
    assert run_list_response.status_code == 200
    assert run_list_response.json()[0]["family_id"] == "gregory-transfer-stv"
    assert run_list_response.json()[0]["method_name"] == "inclusive-gregory"

    run_detail_response = client.get(f"/runs/{persisted_run.summary.run_id}")
    assert run_detail_response.status_code == 200
    assert run_detail_response.json()["summary"]["run_id"] == str(
        persisted_run.summary.run_id
    )

    missing_response = client.get(f"/runs/{uuid4()}")
    assert missing_response.status_code == 404
    assert missing_response.json()["detail"] == "Contest run not found"


def test_default_trace_api_uses_duckdb_store_for_empty_database(
    tmp_path: Path,
) -> None:
    """The default API factory should create a working app against an empty DuckDB file."""
    client = TestClient(
        create_default_trace_api(database_path=tmp_path / "trace.duckdb")
    )

    assert client.get("/health").status_code == 200
    assert client.get("/runs").json() == []
