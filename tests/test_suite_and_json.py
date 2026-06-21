"""Tests for the suite front-door features: --json on every command, the
cpa-workpaper-spec doc-type linting path, and suite-wired scaffolding."""

from __future__ import annotations

import json
from pathlib import Path

import yaml
from typer.testing import CliRunner

from maxed_cli.cli import app
from maxed_cli.suite import SUITE, suite_as_dict
from maxed_cli.workpaper import KNOWN_DOC_TYPES, lint_spec

runner = CliRunner()

VALID_CONFIG = {
    "version": 1,
    "firm": {"name": "Example CPA", "slug": "example-cpa"},
    "workspace": {"root": "./ws"},
    "connectors": [{"name": "ledger", "kind": "mock-ledger"}],
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


# --- suite catalog ----------------------------------------------------------


def test_suite_catalog_shape() -> None:
    records = suite_as_dict()
    names = {r["name"] for r in records}
    assert {"accounting-adapters", "statement-normalizer"} <= names
    for rec in records:
        assert rec["repo"].startswith("https://github.com/maxed-oss/")


def test_suite_command_text() -> None:
    result = runner.invoke(app, ["suite"])
    assert result.exit_code == 0
    assert "accounting-adapters" in result.stdout
    assert "statement-normalizer" in result.stdout


def test_suite_command_json() -> None:
    result = runner.invoke(app, ["suite", "--json"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert len(payload["suite"]) == len(SUITE)


# --- --json on every command ------------------------------------------------


def test_validate_config_json_ok(tmp_path: Path) -> None:
    cfg = _yaml(tmp_path / "c.yaml", VALID_CONFIG)
    result = runner.invoke(app, ["validate-config", str(cfg), "--json"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["errors"] == []


def test_validate_config_json_invalid(tmp_path: Path) -> None:
    cfg = _json(tmp_path / "c.json", {"version": 1})
    result = runner.invoke(app, ["validate-config", str(cfg), "--json"])
    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["errors"]


def test_lint_workpaper_json_ok(tmp_path: Path) -> None:
    wp = _json(tmp_path / "wp.json", VALID_WORKPAPER)
    result = runner.invoke(app, ["lint-workpaper", str(wp), "--json"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["doc_type"] == "workpaper"


def test_lint_workpaper_json_invalid(tmp_path: Path) -> None:
    bad = {k: v for k, v in VALID_WORKPAPER.items() if k != "sections"}
    wp = _json(tmp_path / "wp.json", bad)
    result = runner.invoke(app, ["lint-workpaper", str(wp), "--json"])
    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    assert payload["ok"] is False


def test_init_json(tmp_path: Path) -> None:
    cfg = _yaml(tmp_path / "c.yaml", VALID_CONFIG)
    result = runner.invoke(
        app, ["init", str(cfg), "--base-dir", str(tmp_path), "--json"]
    )
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["created"]


# --- suite-wired scaffolding ------------------------------------------------


def test_init_scaffolds_suite_wiring(tmp_path: Path) -> None:
    cfg = _yaml(tmp_path / "c.yaml", VALID_CONFIG)
    runner.invoke(app, ["init", str(cfg), "--base-dir", str(tmp_path)])
    ws = tmp_path / "ws"
    reqs = ws / "requirements.txt"
    pipeline = ws / "pipeline" / "import_transactions.py"
    statement = ws / "fixtures" / "statement.csv"
    close_doc = ws / "workpapers" / "example.close-checklist.json"

    assert reqs.is_file()
    text = reqs.read_text(encoding="utf-8")
    assert "accounting-adapters" in text
    assert "statement-normalizer" in text

    assert pipeline.is_file()
    src = pipeline.read_text(encoding="utf-8")
    assert "from statement_normalizer import normalize_file" in src
    assert "accounting_adapters" in src

    assert statement.is_file()
    assert "Amount" in statement.read_text(encoding="utf-8")

    assert close_doc.is_file()


# --- cpa-workpaper-spec doc-type linting (offline, self-contained) -----------

# A tiny self-contained spec dir so the doc-type path is exercised without
# depending on a sibling checkout being present.
_COMMON_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "common.schema.json",
    "$defs": {
        "id": {"type": "string", "minLength": 1},
        "specVersion": {"type": "string"},
    },
}

_ENGAGEMENT_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "engagement.schema.json",
    "type": "object",
    "required": ["specVersion", "id"],
    "additionalProperties": False,
    "properties": {
        "specVersion": {"$ref": "common.schema.json#/$defs/specVersion"},
        "id": {"$ref": "common.schema.json#/$defs/id"},
        "title": {"type": "string"},
    },
}


def _spec_dir(tmp_path: Path) -> Path:
    d = tmp_path / "schema" / "v0.1"
    d.mkdir(parents=True)
    (d / "common.schema.json").write_text(json.dumps(_COMMON_SCHEMA))
    (d / "engagement.schema.json").write_text(json.dumps(_ENGAGEMENT_SCHEMA))
    return d


def test_known_doc_types_include_spec_types() -> None:
    assert "engagement" in KNOWN_DOC_TYPES
    assert "close-checklist" in KNOWN_DOC_TYPES


def test_lint_spec_doctype_requires_spec_dir() -> None:
    from maxed_cli.config import ConfigError

    try:
        lint_spec({"specVersion": "0.1", "id": "x"}, doc_type="engagement")
    except ConfigError as exc:
        assert "spec-dir" in str(exc).replace("_", "-")
    else:  # pragma: no cover
        raise AssertionError("expected ConfigError")


def test_lint_workpaper_engagement_ok(tmp_path: Path) -> None:
    sd = _spec_dir(tmp_path)
    doc = _json(tmp_path / "e.json", {"specVersion": "0.1", "id": "eng-1"})
    result = runner.invoke(
        app,
        ["lint-workpaper", str(doc), "--doc-type", "engagement", "--spec-dir", str(sd), "--json"],
    )
    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["doc_type"] == "engagement"


def test_lint_workpaper_engagement_invalid(tmp_path: Path) -> None:
    sd = _spec_dir(tmp_path)
    doc = _json(tmp_path / "e.json", {"id": "eng-1"})  # missing specVersion
    result = runner.invoke(
        app,
        ["lint-workpaper", str(doc), "--doc-type", "engagement", "--spec-dir", str(sd), "--json"],
    )
    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["errors"]


def test_lint_unknown_doc_type(tmp_path: Path) -> None:
    doc = _json(tmp_path / "e.json", {"id": "x"})
    result = runner.invoke(app, ["lint-workpaper", str(doc), "--doc-type", "nope"])
    assert result.exit_code == 2


def test_scaffolded_close_checklist_lints_against_real_spec(tmp_path: Path) -> None:
    """If a cpa-workpaper-spec checkout is available alongside this repo, the
    scaffolded close-checklist example must validate against its real schema.

    Skips cleanly when the sibling checkout is not present (e.g. on CI that only
    checks out this repo).
    """
    import pytest

    # Look for a sibling cpa-workpaper-spec checkout relative to this repo root.
    repo_root = Path(__file__).resolve().parents[1]
    candidates = [
        repo_root.parent / "cpa-workpaper-spec" / "schema" / "v0.1",
        repo_root / "cpa-workpaper-spec" / "schema" / "v0.1",
    ]
    spec_dir = next((c for c in candidates if c.is_dir()), None)
    if spec_dir is None:
        pytest.skip("cpa-workpaper-spec checkout not available")

    cfg = _yaml(tmp_path / "c.yaml", VALID_CONFIG)
    runner.invoke(app, ["init", str(cfg), "--base-dir", str(tmp_path)])
    close_doc = tmp_path / "ws" / "workpapers" / "example.close-checklist.json"

    result = runner.invoke(
        app,
        [
            "lint-workpaper",
            str(close_doc),
            "--doc-type",
            "close-checklist",
            "--spec-dir",
            str(spec_dir),
            "--json",
        ],
    )
    assert result.exit_code == 0, result.stdout
    assert json.loads(result.stdout)["ok"] is True
