"""Relational schema definitions for persisted contest traces.

This module holds the durable database shape used by the DuckDB backend. The split
between Pydantic domain models and SQLAlchemy tables is intentional: in-memory models
stay focused on validated application behavior, while the schema here describes how the
same information is stored, indexed, and reconstructed in a relational database.
"""

from sqlalchemy import DateTime, Integer, MetaData, String, Table, Text, Uuid, func
from sqlalchemy.schema import Column

TRACE_METADATA = MetaData()


contest_runs_table = Table(
    "contest_runs",
    TRACE_METADATA,
    Column(
        "run_id",
        Uuid,
        primary_key=True,
        comment=(
            "Primary identifier for one contest run. UUIDv7 values remain globally "
            "unique and roughly sortable by creation time."
        ),
    ),
    Column(
        "created_at",
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
        comment="Timestamp recording when the run row was persisted.",
    ),
    Column(
        "family_id",
        String,
        nullable=False,
        comment="Stable family identifier for the counting method used for this run.",
    ),
    Column(
        "method_name",
        String,
        nullable=False,
        comment="Public label used to describe the counting method for this run.",
    ),
    Column(
        "selected_option_ids_json",
        Text,
        nullable=False,
        comment="JSON array of the final selected option identifiers.",
    ),
    Column(
        "contest_data_json",
        Text,
        nullable=False,
        comment=(
            "JSON serialization of the immutable contest input data. This is stored "
            "inline as a reconstruction artifact for now, but may eventually move to "
            "a separate contests table if large contest inputs or repeated runs over "
            "the same contest become common."
        ),
    ),
    Column(
        "event_count",
        Integer,
        nullable=False,
        comment="Total number of persisted event rows for this run.",
    ),
    Column(
        "snapshot_count",
        Integer,
        nullable=False,
        comment="Total number of persisted snapshot steps for this run.",
    ),
    comment="One row per counted contest run.",
)


contest_events_table = Table(
    "contest_events",
    TRACE_METADATA,
    Column(
        "run_id",
        Uuid,
        nullable=False,
        comment="Identifier of the contest run that produced this event.",
    ),
    Column(
        "step_index",
        Integer,
        nullable=False,
        comment="Canonical ordering index across all trace records within a run.",
    ),
    Column(
        "phase_type",
        String,
        nullable=False,
        comment="Method-agnostic phase label such as initial, round, or iteration.",
    ),
    Column(
        "phase_index",
        Integer,
        nullable=False,
        comment="Ordinal index within the current phase type.",
    ),
    Column(
        "round_number",
        Integer,
        nullable=True,
        comment="Optional round index for round-based methods.",
    ),
    Column(
        "iteration_number",
        Integer,
        nullable=True,
        comment="Optional iteration index for iterative methods.",
    ),
    Column(
        "event_type",
        String,
        nullable=False,
        comment="Structured event category recorded by the counting method.",
    ),
    Column(
        "option_id",
        String,
        nullable=True,
        comment="Optional option identifier associated with the event.",
    ),
    Column(
        "participant_id",
        String,
        nullable=True,
        comment="Optional participant identifier associated with the event.",
    ),
    Column(
        "message",
        Text,
        nullable=False,
        comment="Human-readable event summary.",
    ),
    Column(
        "details_json",
        Text,
        nullable=False,
        comment="JSON object carrying structured event details.",
    ),
    comment="One row per structured trace event.",
)


contest_snapshots_table = Table(
    "contest_snapshots",
    TRACE_METADATA,
    Column(
        "run_id",
        Uuid,
        nullable=False,
        comment="Identifier of the contest run that produced this snapshot row.",
    ),
    Column(
        "step_index",
        Integer,
        nullable=False,
        comment="Canonical ordering index across all trace records within a run.",
    ),
    Column(
        "phase_type",
        String,
        nullable=False,
        comment="Method-agnostic phase label for the snapshot step.",
    ),
    Column(
        "phase_index",
        Integer,
        nullable=False,
        comment="Ordinal index within the current phase type.",
    ),
    Column(
        "round_number",
        Integer,
        nullable=True,
        comment="Optional round index for round-based methods.",
    ),
    Column(
        "iteration_number",
        Integer,
        nullable=True,
        comment="Optional iteration index for iterative methods.",
    ),
    Column(
        "option_id",
        String,
        nullable=False,
        comment="Option identifier represented in the snapshot row.",
    ),
    Column(
        "tally",
        Text,
        nullable=False,
        comment="Current tally for the option at this snapshot step.",
    ),
    Column(
        "threshold",
        Text,
        nullable=False,
        comment="Current threshold for the option at this snapshot step.",
    ),
    Column(
        "status",
        String,
        nullable=False,
        comment="Current option status at this snapshot step.",
    ),
    Column(
        "exhausted_value",
        Text,
        nullable=False,
        comment="Total exhausted ballot value at this snapshot step.",
    ),
    comment="One row per option per snapshot step.",
)


TRACE_TABLES: tuple[Table, ...] = (
    contest_runs_table,
    contest_events_table,
    contest_snapshots_table,
)
