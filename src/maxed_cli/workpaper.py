"""Workpaper-spec linting.

Linting is a two-step process:

1. Structural validation against the bundled JSON Schema.
2. Semantic checks that the schema cannot express (uniqueness of keys/refs).

The linter is firm-agnostic and operates only on declarative specs; it never
reads or produces real client financial data.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List

from .config import load_document
from .schemas import WORKPAPER_SCHEMA, load_schema
from .config import validate_document


@dataclass
class LintResult:
    """Outcome of linting a workpaper spec."""

    ok: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


def _semantic_checks(spec: Dict[str, Any]) -> LintResult:
    """Checks beyond JSON Schema: unique section keys and unique line refs."""
    errors: List[str] = []
    warnings: List[str] = []

    sections = spec.get("sections", [])
    seen_section_keys: Dict[str, int] = {}
    seen_refs: Dict[str, str] = {}

    for s_idx, section in enumerate(sections):
        if not isinstance(section, dict):
            continue
        key = section.get("key")
        if isinstance(key, str):
            if key in seen_section_keys:
                errors.append(
                    f"sections/{s_idx}/key: duplicate section key '{key}' "
                    f"(first seen at sections/{seen_section_keys[key]})"
                )
            else:
                seen_section_keys[key] = s_idx

        for l_idx, item in enumerate(section.get("line_items", []) or []):
            if not isinstance(item, dict):
                continue
            ref = item.get("ref")
            if isinstance(ref, str):
                if ref in seen_refs:
                    errors.append(
                        f"sections/{s_idx}/line_items/{l_idx}/ref: duplicate "
                        f"line-item ref '{ref}' (first seen in {seen_refs[ref]})"
                    )
                else:
                    seen_refs[ref] = f"sections/{s_idx}/line_items/{l_idx}"

        if not (section.get("line_items") or []):
            warnings.append(
                f"sections/{s_idx}: section '{key or s_idx}' has no line items"
            )

    return LintResult(ok=not errors, errors=errors, warnings=warnings)


def lint_spec(spec: Dict[str, Any]) -> LintResult:
    """Lint an already-parsed workpaper spec.

    Runs schema validation first; if that fails, semantic checks are skipped
    (they assume a structurally valid document).
    """
    schema = load_schema(WORKPAPER_SCHEMA)
    structural = validate_document(spec, schema)
    if not structural.ok:
        return LintResult(ok=False, errors=structural.errors)

    return _semantic_checks(spec)


def lint_file(path: Path) -> LintResult:
    """Load and lint a workpaper-spec file (JSON or YAML)."""
    document = load_document(path)
    return lint_spec(document)
