"""CLI for ranchobud."""

from pathlib import Path

import click


@click.command()
@click.argument("input_file", type=click.Path(exists=True))
@click.argument("output_file", type=click.Path())
def run_ranchobud(input_file: Path, output_file: Path) -> None:
    """Run the ranchobud algorithm."""
    click.echo(f"Running ranchobud with {input_file} and {output_file}")


if __name__ == "__main__":
    run_ranchobud()
