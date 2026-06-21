"""``maxed`` command-line interface — the front door to the open-source suite.

Subcommands:

* ``maxed init`` — scaffold a local developer workspace pre-wired to use the
  sibling libraries (accounting-adapters, statement-normalizer) and the
  cpa-workpaper-spec vocabulary.
* ``maxed validate-config`` — validate a workspace config file.
* ``maxed lint-workpaper`` — lint a workpaper-spec JSON against the bundled
  schema, or validate any cpa-workpaper-spec doc type.
* ``maxed smoke`` — run sandbox/mock connector smoke-tests from a config.
* ``maxed suite`` — show the open-source suite this CLI is the on-ramp to.

Every command supports ``--json`` for machine-readable, agent-friendly output.
All commands operate locally on synthetic data only.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

import typer

from . import __version__
from .config import ConfigError, load_document, validate_config_file
from .connectors import build_connector
from .connectors.base import ConnectorError
from .scaffold import scaffold_workspace
from .suite import suite_as_dict
from .workpaper import KNOWN_DOC_TYPES, lint_file

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="Front-door CLI for the open-source accounting-tech suite.",
)


def _emit_json(payload: Dict[str, Any]) -> None:
    """Print a JSON payload on stdout (agent-friendly, deterministic)."""
    typer.echo(json.dumps(payload, indent=2, sort_keys=True))


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
    as_json: bool = typer.Option(
        False, "--json", help="Emit machine-readable JSON results."
    ),
) -> None:
    """Validate a workspace config file against the bundled schema."""
    try:
        result = validate_config_file(path)
    except ConfigError as exc:
        if as_json:
            _emit_json({"path": str(path), "ok": False, "error": str(exc)})
        else:
            typer.secho(f"error: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=2)

    if as_json:
        _emit_json({"path": str(path), "ok": result.ok, "errors": result.errors})
        raise typer.Exit(code=0 if result.ok else 1)

    if result.ok:
        typer.secho(f"OK: {path} is a valid workspace config", fg=typer.colors.GREEN)
        return

    typer.secho(f"INVALID: {path}", fg=typer.colors.RED, err=True)
    for err in result.errors:
        typer.secho(f"  - {err}", fg=typer.colors.RED, err=True)
    raise typer.Exit(code=1)


@app.command("lint-workpaper")
def lint_workpaper(
    path: Path = typer.Argument(..., help="Path to a workpaper / spec doc (JSON/YAML)."),
    doc_type: str = typer.Option(
        "workpaper",
        "--doc-type",
        help=(
            "Document type to validate against. 'workpaper' uses the bundled "
            "schema; the cpa-workpaper-spec types (engagement, close-checklist, "
            "tax-prep, engagement-letter, request-list-item) require --spec-dir."
        ),
    ),
    spec_dir: Optional[Path] = typer.Option(
        None,
        "--spec-dir",
        help=(
            "A cpa-workpaper-spec checkout's schema/<version>/ directory "
            "(required for non-'workpaper' doc types)."
        ),
    ),
    strict: bool = typer.Option(
        False, "--strict", help="Treat warnings as failures."
    ),
    as_json: bool = typer.Option(
        False, "--json", help="Emit machine-readable JSON results."
    ),
) -> None:
    """Lint a workpaper-spec file, or validate any cpa-workpaper-spec doc type."""
    try:
        result = lint_file(path, doc_type=doc_type, spec_dir=spec_dir)
    except ConfigError as exc:
        if as_json:
            _emit_json(
                {"path": str(path), "doc_type": doc_type, "ok": False, "error": str(exc)}
            )
        else:
            typer.secho(f"error: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=2)

    failed_strict = bool(strict and result.warnings)
    passed = result.ok and not failed_strict

    if as_json:
        _emit_json(
            {
                "path": str(path),
                "doc_type": result.doc_type,
                "ok": passed,
                "errors": result.errors,
                "warnings": result.warnings,
                "strict": strict,
            }
        )
        raise typer.Exit(code=0 if passed else 1)

    for warning in result.warnings:
        typer.secho(f"  warning: {warning}", fg=typer.colors.YELLOW)

    if passed:
        suffix = " (warnings present)" if result.warnings else ""
        typer.secho(
            f"OK: {path} is a valid {result.doc_type}{suffix}", fg=typer.colors.GREEN
        )
        return

    if not result.ok:
        typer.secho(f"INVALID: {path}", fg=typer.colors.RED, err=True)
        for err in result.errors:
            typer.secho(f"  - {err}", fg=typer.colors.RED, err=True)
    else:
        typer.secho(
            f"FAILED (strict): {path} has warnings", fg=typer.colors.RED, err=True
        )
    raise typer.Exit(code=1)


@app.command("init")
def init(
    config: Path = typer.Argument(..., help="Path to a workspace config (YAML/JSON)."),
    base_dir: Path = typer.Option(
        Path("."),
        "--base-dir",
        help="Directory to resolve a relative workspace root against.",
    ),
    as_json: bool = typer.Option(
        False, "--json", help="Emit machine-readable JSON results."
    ),
) -> None:
    """Scaffold a suite-wired developer workspace from a config file."""
    try:
        result = validate_config_file(config)
    except ConfigError as exc:
        if as_json:
            _emit_json({"config": str(config), "ok": False, "error": str(exc)})
        else:
            typer.secho(f"error: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=2)

    if not result.ok:
        if as_json:
            _emit_json({"config": str(config), "ok": False, "errors": result.errors})
        else:
            typer.secho(f"INVALID config: {config}", fg=typer.colors.RED, err=True)
            for err in result.errors:
                typer.secho(f"  - {err}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)

    document = load_document(config)
    outcome = scaffold_workspace(document, base_dir)

    if as_json:
        _emit_json(
            {
                "config": str(config),
                "ok": True,
                "root": str(outcome.root),
                "created": [str(p) for p in outcome.created],
                "existed": [str(p) for p in outcome.existed],
            }
        )
        return

    typer.secho(f"Scaffolded workspace at {outcome.root}", fg=typer.colors.GREEN)
    for path in outcome.created:
        typer.echo(f"  created  {path}")
    for path in outcome.existed:
        typer.echo(f"  exists   {path}")


@app.command("suite")
def suite(
    as_json: bool = typer.Option(
        False, "--json", help="Emit machine-readable JSON results."
    ),
) -> None:
    """Show the open-source suite this CLI is the on-ramp to."""
    packages = suite_as_dict()
    if as_json:
        _emit_json({"suite": packages})
        return

    typer.secho("maxed is the front door to:", fg=typer.colors.GREEN)
    for pkg in packages:
        typer.secho(f"\n  {pkg['name']}", fg=typer.colors.CYAN, bold=True)
        typer.echo(f"    {pkg['summary']}")
        typer.echo(f"    pip install {pkg['pypi']}")
        typer.echo(f"    {pkg['repo']}")
    typer.echo(
        "\nValid lint-workpaper doc types: " + ", ".join(KNOWN_DOC_TYPES)
    )


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
        if as_json:
            _emit_json({"config": str(config), "ok": False, "error": str(exc)})
        else:
            typer.secho(f"error: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=2)

    if not result.ok:
        if as_json:
            _emit_json({"config": str(config), "ok": False, "errors": result.errors})
        else:
            typer.secho(f"INVALID config: {config}", fg=typer.colors.RED, err=True)
            for err in result.errors:
                typer.secho(f"  - {err}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)

    document = load_document(config)
    connectors = document.get("connectors", []) or []

    if not connectors:
        if as_json:
            typer.echo(json.dumps({"results": []}))
        else:
            typer.secho("No connectors defined in config.", fg=typer.colors.YELLOW)
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
