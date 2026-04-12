"""DuckDB-backed trace persistence built on SQLAlchemy Core.

This backend is the concrete implementation of the storage interfaces used by the rest
of ranchovote. It is responsible for turning completed contest results into relational
rows and reconstructing persisted runs for later analysis, comparison, and interface
consumption.
"""

import json
import uuid
from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from uuid import UUID

from sqlalchemy import create_engine, insert, select
from sqlalchemy.engine import Engine, RowMapping

from ranchovote.io.json import serialize_contest_data
from ranchovote.models import ContestData, OptionId
from ranchovote.state import OptionStatus
from ranchovote.storage.base import TraceRepository, TraceStore
from ranchovote.storage.schema import (
    TRACE_METADATA,
    contest_events_table,
    contest_runs_table,
    contest_snapshots_table,
)
from ranchovote.trace import (
    ContestResult,
    CountEvent,
    PersistedContestRun,
    PersistedContestRunSummary,
    RoundSnapshot,
    TracePhaseType,
)


@dataclass(slots=True)
class DuckDbTraceStore(TraceStore, TraceRepository):
    """Persist and retrieve contest traces from a DuckDB database file."""

    database_path: Path

    def ensure_schema(self) -> None:
        """Create the required tables if they do not already exist."""
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        engine = self._engine()
        try:
            TRACE_METADATA.create_all(engine)
        finally:
            engine.dispose()

    def write_result(
        self,
        *,
        contest_data: ContestData,
        method_name: str,
        result: ContestResult,
    ) -> None:
        """Persist one complete contest run and its trace."""
        run_id = uuid.uuid7()
        self.ensure_schema()

        engine = self._engine()
        try:
            with engine.begin() as connection:
                connection.execute(
                    insert(contest_runs_table),
                    [
                        {
                            "run_id": run_id,
                            "method_name": method_name,
                            "selected_option_ids_json": json.dumps(
                                list(result.selected_option_ids)
                            ),
                            "contest_data_json": json.dumps(
                                serialize_contest_data(contest_data), sort_keys=True
                            ),
                            "event_count": len(result.audit_log),
                            "snapshot_count": len(result.snapshots),
                        }
                    ],
                )

                event_rows = self._event_rows(run_id=run_id, result=result)
                if event_rows:
                    connection.execute(insert(contest_events_table), event_rows)

                snapshot_rows = self._snapshot_rows(run_id=run_id, result=result)
                if snapshot_rows:
                    connection.execute(insert(contest_snapshots_table), snapshot_rows)
        finally:
            engine.dispose()

    def list_runs(self) -> tuple[PersistedContestRunSummary, ...]:
        """Return persisted run summaries in reverse chronological order."""
        self.ensure_schema()
        engine = self._engine()
        try:
            with engine.connect() as connection:
                rows = connection.execute(
                    select(contest_runs_table).order_by(
                        contest_runs_table.c.created_at.desc()
                    )
                ).mappings()
                return tuple(self._summary_from_row(row) for row in rows)
        finally:
            engine.dispose()

    def get_run(self, *, run_id: UUID) -> PersistedContestRun | None:
        """Return one persisted contest run with events and snapshots."""
        self.ensure_schema()
        engine = self._engine()
        try:
            with engine.connect() as connection:
                run_row = (
                    connection.execute(
                        select(contest_runs_table).where(
                            contest_runs_table.c.run_id == run_id
                        )
                    )
                    .mappings()
                    .one_or_none()
                )
                if run_row is None:
                    return None

                event_rows = (
                    connection.execute(
                        select(contest_events_table)
                        .where(contest_events_table.c.run_id == run_id)
                        .order_by(contest_events_table.c.step_index)
                    )
                    .mappings()
                    .all()
                )
                snapshot_rows = (
                    connection.execute(
                        select(contest_snapshots_table)
                        .where(contest_snapshots_table.c.run_id == run_id)
                        .order_by(
                            contest_snapshots_table.c.step_index,
                            contest_snapshots_table.c.option_id,
                        )
                    )
                    .mappings()
                    .all()
                )

                return PersistedContestRun(
                    summary=self._summary_from_row(run_row),
                    contest_data=ContestData.model_validate(
                        json.loads(run_row["contest_data_json"])
                    ),
                    audit_log=tuple(self._event_from_row(row) for row in event_rows),
                    snapshots=self._snapshots_from_rows(snapshot_rows),
                )
        finally:
            engine.dispose()

    def _engine(self) -> Engine:
        """Return a SQLAlchemy engine for the configured DuckDB database."""
        return create_engine(f"duckdb:///{self.database_path}")

    def _event_rows(
        self,
        *,
        run_id: UUID,
        result: ContestResult,
    ) -> list[dict[str, object]]:
        """Return SQLAlchemy insert payloads for persisted event rows."""
        return [
            {
                "run_id": run_id,
                "step_index": event.step_index,
                "phase_type": event.phase_type.value,
                "phase_index": event.phase_index,
                "round_number": event.round_number,
                "iteration_number": event.iteration_number,
                "event_type": event.event_type,
                "option_id": event.option_id,
                "participant_id": event.participant_id,
                "message": event.message,
                "details_json": json.dumps(event.details, sort_keys=True),
            }
            for event in result.audit_log
        ]

    def _snapshot_rows(
        self,
        *,
        run_id: UUID,
        result: ContestResult,
    ) -> list[dict[str, object]]:
        """Return SQLAlchemy insert payloads for persisted snapshot rows."""
        rows: list[dict[str, object]] = []
        for snapshot in result.snapshots:
            for option_id, status in snapshot.statuses.items():
                rows.append(
                    {
                        "run_id": run_id,
                        "step_index": snapshot.step_index,
                        "phase_type": snapshot.phase_type.value,
                        "phase_index": snapshot.phase_index,
                        "round_number": snapshot.round_number,
                        "iteration_number": snapshot.iteration_number,
                        "option_id": option_id,
                        "tally": self._decimal_string(snapshot.tallies.get(option_id)),
                        "threshold": self._decimal_string(
                            snapshot.thresholds.get(option_id)
                        ),
                        "status": status.value,
                        "exhausted_value": self._decimal_string(
                            snapshot.exhausted_value
                        ),
                    }
                )
        return rows

    def _summary_from_row(self, row: RowMapping) -> PersistedContestRunSummary:
        """Build a persisted run summary from one database row."""
        return PersistedContestRunSummary(
            run_id=row["run_id"],
            created_at=row["created_at"],
            method_name=row["method_name"],
            selected_option_ids=tuple(json.loads(row["selected_option_ids_json"])),
            event_count=row["event_count"],
            snapshot_count=row["snapshot_count"],
        )

    def _event_from_row(self, row: RowMapping) -> CountEvent:
        """Build one count event from a persisted event row."""
        return CountEvent(
            step_index=row["step_index"],
            phase_type=TracePhaseType(row["phase_type"]),
            phase_index=row["phase_index"],
            round_number=row["round_number"],
            iteration_number=row["iteration_number"],
            event_type=row["event_type"],
            message=row["message"],
            option_id=row["option_id"],
            participant_id=row["participant_id"],
            details=dict(json.loads(row["details_json"])),
        )

    def _snapshots_from_rows(
        self,
        rows: Iterable[RowMapping],
    ) -> tuple[RoundSnapshot, ...]:
        """Reconstruct round snapshots from per-option persisted rows."""
        grouped_snapshots: list[RoundSnapshot] = []
        current_key: tuple[int, str, int, int | None, int | None] | None = None
        tallies: dict[OptionId, Decimal] = {}
        thresholds: dict[OptionId, Decimal] = {}
        statuses: dict[OptionId, OptionStatus] = {}
        exhausted_value = Decimal(0)

        for row in rows:
            row_key = (
                row["step_index"],
                row["phase_type"],
                row["phase_index"],
                row["round_number"],
                row["iteration_number"],
            )
            if current_key is None:
                current_key = row_key

            if row_key != current_key:
                grouped_snapshots.append(
                    self._snapshot_from_group(
                        exhausted_value=exhausted_value,
                        key=current_key,
                        statuses=statuses,
                        tallies=tallies,
                        thresholds=thresholds,
                    )
                )
                tallies = {}
                thresholds = {}
                statuses = {}
                current_key = row_key

            option_id = row["option_id"]
            tallies[option_id] = Decimal(row["tally"])
            thresholds[option_id] = Decimal(row["threshold"])
            statuses[option_id] = OptionStatus(row["status"])
            exhausted_value = Decimal(row["exhausted_value"])

        if current_key is not None:
            grouped_snapshots.append(
                self._snapshot_from_group(
                    exhausted_value=exhausted_value,
                    key=current_key,
                    statuses=statuses,
                    tallies=tallies,
                    thresholds=thresholds,
                )
            )

        return tuple(grouped_snapshots)

    def _snapshot_from_group(
        self,
        *,
        exhausted_value: Decimal,
        key: tuple[int, str, int, int | None, int | None],
        statuses: dict[OptionId, OptionStatus],
        tallies: dict[OptionId, Decimal],
        thresholds: dict[OptionId, Decimal],
    ) -> RoundSnapshot:
        """Build one snapshot model from a grouped set of project rows."""
        step_index, phase_type, phase_index, round_number, iteration_number = key
        return RoundSnapshot(
            step_index=step_index,
            phase_type=TracePhaseType(phase_type),
            phase_index=phase_index,
            round_number=round_number,
            iteration_number=iteration_number,
            tallies=dict(tallies),
            thresholds=dict(thresholds),
            statuses=dict(statuses),
            exhausted_value=exhausted_value,
        )

    def _decimal_string(self, value: object) -> str:
        """Return a stable string representation for persisted decimal-like values."""
        if value is None:
            return ""
        return format(value, "f")
