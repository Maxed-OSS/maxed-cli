"""Workspace config loading and validation.

A workspace config is a small YAML/JSON document that describes a local
CPA-firm developer workspace: the firm placeholder, where to scaffold folders,
and which sandbox connectors to register. It carries no secrets and never
points at real client systems.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List

import yaml
from jsonschema import Draft7Validator

from .schemas import CONFIG_SCHEMA, load_schema


@dataclass
class ValidationResult:
    """Outcome of validating a document against a schema."""

    ok: bool
    errors: List[str] = field(default_factory=list)


class ConfigError(Exception):
    """Raised when a config file cannot be read or parsed."""


def load_document(path: Path) -> Dict[str, Any]:
    """Load a YAML or JSON document from disk.

    Args:
        path: File to read. ``.json`` is parsed as JSON; everything else
            (``.yaml``/``.yml``) is parsed as YAML. YAML is a superset of
            JSON, so YAML parsing also accepts JSON input.

    Raises:
        ConfigError: If the file is missing, unreadable, or not a mapping.
    """
    if not path.exists():
        raise ConfigError(f"file not found: {path}")
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:  # pragma: no cover - filesystem edge
        raise ConfigError(f"could not read {path}: {exc}") from exc

    try:
        if path.suffix.lower() == ".json":
            data = json.loads(raw)
        else:
            data = yaml.safe_load(raw)
    except (json.JSONDecodeError, yaml.YAMLError) as exc:
        raise ConfigError(f"could not parse {path}: {exc}") from exc

    if data is None:
        raise ConfigError(f"empty document: {path}")
    if not isinstance(data, dict):
        raise ConfigError(f"top-level document must be a mapping in {path}")
    return data


def _format_error(error) -> str:
    """Render a jsonschema error as a stable, human-readable line."""
    location = "/".join(str(p) for p in error.absolute_path)
    where = f"{location}: " if location else ""
    return f"{where}{error.message}"


def validate_document(document: Dict[str, Any], schema: Dict[str, Any]) -> ValidationResult:
    """Validate a parsed document against a JSON Schema.

    Errors are sorted for deterministic output.
    """
    validator = Draft7Validator(schema)
    errors = sorted(validator.iter_errors(document), key=lambda e: list(e.absolute_path))
    messages = [_format_error(e) for e in errors]
    return ValidationResult(ok=not messages, errors=messages)


def validate_config_file(path: Path) -> ValidationResult:
    """Load and validate a workspace config file.

    Raises:
        ConfigError: If the file cannot be loaded/parsed.
    """
    document = load_document(path)
    schema = load_schema(CONFIG_SCHEMA)
    return validate_document(document, schema)
