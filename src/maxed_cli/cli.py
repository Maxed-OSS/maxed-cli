"""``maxed`` command-line interface.

Subcommands:

* ``maxed init`` — scaffold a local CPA-firm developer workspace.
* ``maxed validate-config`` — validate a workspace config file.
* ``maxed lint-workpaper`` — lint a workpaper-spec JSON against the schema.
* ``maxed smoke`` — run sandbox/mock connector smoke-tests from a config.

All commands operate locally on synthetic data only.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer

from . import __version__
from .config import ConfigError, load_document, validate_config_file
from .connectors import build_connector
from .connectors.base import ConnectorError
from .scaffold import scaffold_workspace
from .workpaper import lint_file

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="Developer/operator on-ramp CLI for an accounting-tech stack.",
)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"maxed {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        False,
        "--version",
        callback=_version_callback,
        is_eager=True,
        help="Show the version and exit.",
    ),
) -> None:
    """maxed: scaffold, validate, lint, and smoke-test locally."""


@app.command("validate-config")
def validate_config(
    path: Path = typer.Argument(..., help="Path to a workspace config (YAML/JSON)."),
) -> None:
    """Validate a workspace config file against the bundled schema."""
    try:
        result = validate_config_file(path)
    except ConfigError as exc:
        typer.secho(f"error: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=2)

    if result.ok:
        typer.secho(f"OK: {path} is a valid workspace config", fg=typer.colors.GREEN)
        return

    typer.secho(f"INVALID: {path}", fg=typer.colors.RED, err=True)
    for err in result.errors:
        typer.secho(f"  - {err}", fg=typer.colors.RED, err=True)
    raise typer.Exit(code=1)


@app.command("lint-workpaper")
def lint_workpaper(
    path: Path = typer.Argument(..., help="Path to a workpaper spec (JSON/YAML)."),
    strict: bool = typer.Option(
        False, "--strict", help="Treat warnings as failures."
    ),
) -> None:
    """Lint a workpaper-spec file against the schema and run semantic checks."""
    try:
        result = lint_file(path)
    except ConfigError as exc:
        typer.secho(f"error: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=2)

    for warning in result.warnings:
        typer.secho(f"  warning: {warning}", fg=typer.colors.YELLOW)

    if result.ok and not (strict and result.warnings):
        suffix = " (warnings present)" if result.warnings else ""
        typer.secho(f"OK: {path} is a valid workpaper spec{suffix}", fg=typer.colors.GREEN)
        return

    if not result.ok:
        typer.secho(f"INVALID: {path}", fg=typer.colors.RED, err=True)
        for err in result.errors:
            typer.secho(f"  - {err}", fg=typer.colors.RED, err=True)
    else:
        typer.secho(f"FAILED (strict): {path} has warnings", fg=typer.colors.RED, err=True)
    raise typer.Exit(code=1)


@app.command("init")
def init(
    config: Path = typer.Argument(..., help="Path to a workspace config (YAML/JSON)."),
    base_dir: Path = typer.Option(
        Path("."),
        "--base-dir",
        help="Directory to resolve a relative workspace root against.",
    ),
) -> None:
    """Scaffold a local developer workspace from a config file."""
    try:
        result = validate_config_file(config)
    except ConfigError as exc:
        typer.secho(f"error: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=2)

    if not result.ok:
        typer.secho(f"INVALID config: {config}", fg=typer.colors.RED, err=True)
        for err in result.errors:
            typer.secho(f"  - {err}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)

    document = load_document(config)
    outcome = scaffold_workspace(document, base_dir)

    typer.secho(f"Scaffolded workspace at {outcome.root}", fg=typer.colors.GREEN)
    for path in outcome.created:
        typer.echo(f"  created  {path}")
    for path in outcome.existed:
        typer.echo(f"  exists   {path}")


@app.command("smoke")
def smoke(
    config: Path = typer.Argument(..., help="Path to a workspace config (YAML/JSON)."),
    as_json: bool = typer.Option(
        False, "--json", help="Emit machine-readable JSON results."
    ),
) -> None:
    """Run sandbox/mock connector smoke-tests defined in a config.

    Connectors are pure in-process simulations on synthetic fixtures; nothing
    here touches the network or any real system.
    """
    try:
        result = validate_config_file(config)
    except ConfigError as exc:
        typer.secho(f"error: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=2)

    if not result.ok:
        typer.secho(f"INVALID config: {config}", fg=typer.colors.RED, err=True)
        for err in result.errors:
            typer.secho(f"  - {err}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)

    document = load_document(config)
    connectors = document.get("connectors", []) or []

    if not connectors:
        typer.secho("No connectors defined in config.", fg=typer.colors.YELLOW)
        if as_json:
            typer.echo(json.dumps({"results": []}))
        return

    results = []
    failures = 0
    for spec in connectors:
        try:
            connector = build_connector(
                name=spec["name"], kind=spec["kind"], options=spec.get("options")
            )
            outcome = connector.smoke()
        except ConnectorError as exc:
            failures += 1
            results.append(
                {
                    "name": spec.get("name", "?"),
                    "kind": spec.get("kind", "?"),
                    "ok": False,
                    "detail": str(exc),
                }
            )
            continue

        if not outcome.ok:
            failures += 1
        results.append(
            {
                "name": outcome.name,
                "kind": outcome.kind,
                "ok": outcome.ok,
                "detail": outcome.detail,
                "data": outcome.data,
            }
        )

    if as_json:
        typer.echo(json.dumps({"results": results}, indent=2))
    else:
        for r in results:
            mark = "PASS" if r["ok"] else "FAIL"
            color = typer.colors.GREEN if r["ok"] else typer.colors.RED
            typer.secho(
                f"  [{mark}] {r['name']} ({r['kind']}): {r['detail']}", fg=color
            )
        total = len(results)
        passed = total - failures
        typer.secho(
            f"{passed}/{total} connectors passed",
            fg=typer.colors.GREEN if failures == 0 else typer.colors.RED,
        )

    if failures:
        raise typer.Exit(code=1)


if __name__ == "__main__":  # pragma: no cover
    app()
