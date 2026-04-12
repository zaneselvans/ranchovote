"""Tests for the Typer-based ranchovote CLI."""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from ranchovote.cli import app

runner = CliRunner()


def test_cli_help_lists_available_interfaces() -> None:
    """The CLI help should advertise the available interface commands."""
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "api" in result.stdout
    assert "tui" in result.stdout


def test_api_command_runs_uvicorn(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """The API command should build the app and hand it to uvicorn."""
    database_path = tmp_path / "trace.duckdb"
    captured: dict[str, object] = {}

    def fake_create_default_trace_api(*, database_path: Path) -> object:
        captured["database_path"] = database_path
        return "fake-app"

    def fake_uvicorn_run(app_object: object, *, host: str, port: int) -> None:
        captured["app"] = app_object
        captured["host"] = host
        captured["port"] = port

    monkeypatch.setattr(
        "ranchovote.cli.create_default_trace_api", fake_create_default_trace_api
    )
    monkeypatch.setattr("ranchovote.cli.uvicorn.run", fake_uvicorn_run)

    result = runner.invoke(
        app,
        [
            "api",
            "--database",
            str(database_path),
            "--host",
            "127.0.0.1",
            "--port",
            "9000",
        ],
    )

    assert result.exit_code == 0
    assert captured == {
        "database_path": database_path,
        "app": "fake-app",
        "host": "127.0.0.1",
        "port": 9000,
    }


def test_tui_command_runs_textual_app(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """The TUI command should construct the app and call its run method."""
    database_path = tmp_path / "trace.duckdb"
    captured: dict[str, object] = {}

    class FakeApp:
        def run(self) -> None:
            captured["ran"] = True

    def fake_create_default_trace_tui(*, database_path: Path) -> FakeApp:
        captured["database_path"] = database_path
        return FakeApp()

    monkeypatch.setattr(
        "ranchovote.cli.create_default_trace_tui", fake_create_default_trace_tui
    )

    result = runner.invoke(app, ["tui", "--database", str(database_path)])

    assert result.exit_code == 0
    assert captured == {
        "database_path": database_path,
        "ran": True,
    }
