"""End-to-end CLI tests using Typer's test runner."""

from __future__ import annotations

import json
from pathlib import Path

import yaml
from typer.testing import CliRunner

from maxed_cli.cli import app

runner = CliRunner()

VALID_CONFIG = {
    "version": 1,
    "firm": {"name": "Example CPA", "slug": "example-cpa"},
    "workspace": {"root": "./ws"},
    "connectors": [
        {"name": "ledger", "kind": "mock-ledger"},
        {"name": "ping", "kind": "echo", "options": {"note": "hi"}},
    ],
}

VALID_WORKPAPER = {
    "spec_version": 1,
    "id": "WP-X",
    "title": "Example",
    "sections": [
        {
            "key": "s1",
            "label": "Section",
            "line_items": [{"ref": "a", "label": "A", "type": "amount"}],
        }
    ],
}


def _yaml(path: Path, data) -> Path:
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    return path


def _json(path: Path, data) -> Path:
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def test_version() -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "maxed" in result.stdout


def test_help() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "validate-config" in result.stdout
    assert "lint-workpaper" in result.stdout
    assert "smoke" in result.stdout
    assert "init" in result.stdout


def test_validate_config_ok(tmp_path: Path) -> None:
    cfg = _yaml(tmp_path / "c.yaml", VALID_CONFIG)
    result = runner.invoke(app, ["validate-config", str(cfg)])
    assert result.exit_code == 0
    assert "OK" in result.stdout


def test_validate_config_invalid(tmp_path: Path) -> None:
    bad = {"version": 1}
    cfg = _json(tmp_path / "c.json", bad)
    result = runner.invoke(app, ["validate-config", str(cfg)])
    assert result.exit_code == 1


def test_lint_workpaper_ok(tmp_path: Path) -> None:
    wp = _json(tmp_path / "wp.json", VALID_WORKPAPER)
    result = runner.invoke(app, ["lint-workpaper", str(wp)])
    assert result.exit_code == 0
    assert "OK" in result.stdout


def test_lint_workpaper_invalid(tmp_path: Path) -> None:
    bad = dict(VALID_WORKPAPER)
    bad = {k: v for k, v in bad.items() if k != "sections"}
    wp = _json(tmp_path / "wp.json", bad)
    result = runner.invoke(app, ["lint-workpaper", str(wp)])
    assert result.exit_code == 1


def test_init_scaffolds(tmp_path: Path) -> None:
    cfg = _yaml(tmp_path / "c.yaml", VALID_CONFIG)
    result = runner.invoke(app, ["init", str(cfg), "--base-dir", str(tmp_path)])
    assert result.exit_code == 0
    ws = tmp_path / "ws"
    assert ws.is_dir()
    assert (ws / "workpapers").is_dir()
    assert (ws / "configs" / "workspace.json").is_file()
    assert (ws / "workpapers" / "example.workpaper.json").is_file()


def test_init_is_idempotent(tmp_path: Path) -> None:
    cfg = _yaml(tmp_path / "c.yaml", VALID_CONFIG)
    first = runner.invoke(app, ["init", str(cfg), "--base-dir", str(tmp_path)])
    second = runner.invoke(app, ["init", str(cfg), "--base-dir", str(tmp_path)])
    assert first.exit_code == 0
    assert second.exit_code == 0
    assert "exists" in second.stdout


def test_scaffolded_workpaper_lints_clean(tmp_path: Path) -> None:
    cfg = _yaml(tmp_path / "c.yaml", VALID_CONFIG)
    runner.invoke(app, ["init", str(cfg), "--base-dir", str(tmp_path)])
    example = tmp_path / "ws" / "workpapers" / "example.workpaper.json"
    result = runner.invoke(app, ["lint-workpaper", str(example)])
    assert result.exit_code == 0


def test_smoke_passes(tmp_path: Path) -> None:
    cfg = _yaml(tmp_path / "c.yaml", VALID_CONFIG)
    result = runner.invoke(app, ["smoke", str(cfg)])
    assert result.exit_code == 0
    assert "passed" in result.stdout


def test_smoke_json(tmp_path: Path) -> None:
    cfg = _yaml(tmp_path / "c.yaml", VALID_CONFIG)
    result = runner.invoke(app, ["smoke", str(cfg), "--json"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert len(payload["results"]) == 2
    assert all(r["ok"] for r in payload["results"])


def test_smoke_no_connectors(tmp_path: Path) -> None:
    no_conn = {k: v for k, v in VALID_CONFIG.items() if k != "connectors"}
    cfg = _yaml(tmp_path / "c.yaml", no_conn)
    result = runner.invoke(app, ["smoke", str(cfg)])
    assert result.exit_code == 0
    assert "No connectors" in result.stdout


def test_schema_default_is_workpaper() -> None:
    result = runner.invoke(app, ["schema"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["name"] == "workpaper"
    assert payload["schema"].get("$schema") or payload["schema"].get("type")


def test_schema_config_raw_json() -> None:
    result = runner.invoke(app, ["schema", "config", "--json"])
    assert result.exit_code == 0
    schema = json.loads(result.stdout)
    # Raw mode emits the schema itself, not the {name, schema} wrapper.
    assert "name" not in schema or "type" in schema
    assert schema.get("type") == "object"


def test_schema_unknown_name_errors() -> None:
    result = runner.invoke(app, ["schema", "nope"])
    assert result.exit_code == 2
