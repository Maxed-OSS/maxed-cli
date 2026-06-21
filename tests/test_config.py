"""Tests for workspace config loading and validation."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from maxed_cli.config import (
    ConfigError,
    load_document,
    validate_config_file,
)

VALID = {
    "version": 1,
    "firm": {"name": "Example CPA", "slug": "example-cpa"},
    "workspace": {"root": "./ws"},
}


def _write(path: Path, data) -> Path:
    if path.suffix == ".json":
        path.write_text(json.dumps(data), encoding="utf-8")
    else:
        import yaml

        path.write_text(yaml.safe_dump(data), encoding="utf-8")
    return path


def test_valid_config_json(tmp_path: Path) -> None:
    cfg = _write(tmp_path / "c.json", VALID)
    result = validate_config_file(cfg)
    assert result.ok
    assert result.errors == []


def test_valid_config_yaml(tmp_path: Path) -> None:
    cfg = _write(tmp_path / "c.yaml", VALID)
    assert validate_config_file(cfg).ok


def test_missing_required_field(tmp_path: Path) -> None:
    bad = {"version": 1, "workspace": {"root": "./ws"}}
    cfg = _write(tmp_path / "c.json", bad)
    result = validate_config_file(cfg)
    assert not result.ok
    assert any("firm" in e for e in result.errors)


def test_bad_slug_pattern(tmp_path: Path) -> None:
    bad = {
        "version": 1,
        "firm": {"name": "X", "slug": "Not A Slug"},
        "workspace": {"root": "./ws"},
    }
    cfg = _write(tmp_path / "c.json", bad)
    result = validate_config_file(cfg)
    assert not result.ok
    assert any("slug" in e for e in result.errors)


def test_unknown_connector_kind_rejected(tmp_path: Path) -> None:
    bad = dict(VALID)
    bad["connectors"] = [{"name": "x", "kind": "real-prod-thing"}]
    cfg = _write(tmp_path / "c.json", bad)
    result = validate_config_file(cfg)
    assert not result.ok


def test_additional_properties_rejected(tmp_path: Path) -> None:
    bad = dict(VALID)
    bad["surprise"] = True
    cfg = _write(tmp_path / "c.json", bad)
    assert not validate_config_file(cfg).ok


def test_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(ConfigError):
        validate_config_file(tmp_path / "nope.yaml")


def test_non_mapping_raises(tmp_path: Path) -> None:
    p = tmp_path / "list.json"
    p.write_text("[1, 2, 3]", encoding="utf-8")
    with pytest.raises(ConfigError):
        load_document(p)


def test_empty_document_raises(tmp_path: Path) -> None:
    p = tmp_path / "empty.yaml"
    p.write_text("", encoding="utf-8")
    with pytest.raises(ConfigError):
        load_document(p)
