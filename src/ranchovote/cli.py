"""Typer command-line entry points for ranchovote interfaces.

The CLI is intentionally small and acts as a launcher for interface layers such as the
web API and terminal UI. It is not where contest logic lives; its job is to expose the
package's capabilities in a convenient way for local development and exploration.
"""

from pathlib import Path
from typing import Annotated

import typer
import uvicorn
from rich.console import Console

from ranchovote.tui.app import create_default_trace_tui
from ranchovote.web.app import create_default_trace_api

app = typer.Typer(help="Launch the ranchovote trace explorer interfaces.")
console = Console()
DEFAULT_DATABASE_PATH = Path("ranchovote.duckdb")

DatabasePathOption = Annotated[
    Path,
    typer.Option(
        "--database",
        "-d",
        help="Path to the DuckDB trace database.",
    ),
]
HostOption = Annotated[
    str,
    typer.Option(help="Host interface to bind."),
]
PortOption = Annotated[
    int,
    typer.Option(min=1, max=65535, help="Port to bind."),
]


@app.command()
def api(
    database_path: DatabasePathOption = DEFAULT_DATABASE_PATH,
    host: HostOption = "127.0.0.1",
    port: PortOption = 8000,
) -> None:
    """Run the FastAPI trace explorer."""
    console.print(f"Serving trace API from {database_path} on {host}:{port}")
    uvicorn.run(
        create_default_trace_api(database_path=database_path),
        host=host,
        port=port,
    )


@app.command()
def tui(
    database_path: DatabasePathOption = DEFAULT_DATABASE_PATH,
) -> None:
    """Run the Textual trace explorer."""
    console.print(f"Opening trace TUI for {database_path}")
    create_default_trace_tui(database_path=database_path).run()


if __name__ == "__main__":
    app()
