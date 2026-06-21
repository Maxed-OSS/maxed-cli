"""Workpaper / CPA-document linting.

Two linting modes are supported:

1. **Bundled workpaper schema** (``doc_type='workpaper'``, the default). Lints a
   simple section/line-item *workpaper* spec against the schema bundled with
   this package, plus semantic checks the schema cannot express (unique section
   keys, unique line-item refs).

2. **cpa-workpaper-spec doc types.** ``maxed-cli`` is the front door to the
   wider open-source suite, so ``lint-workpaper`` can also validate a document
   against the published `cpa-workpaper-spec
   <https://github.com/maxed-oss/cpa-workpaper-spec>`_ vocabulary — the
   firm-agnostic JSON-Schema standard for ``engagement``, ``close-checklist``,
   ``tax-prep``, ``engagement-letter`` and ``request-list-item`` documents. The
   schemas themselves live in (and are owned by) that sibling repository; we do
   not vendor them. Point ``--spec-dir`` at a checkout's ``schema/<version>/``
   directory and we resolve its cross-file ``$ref`` graph fully offline.

The linter is firm-agnostic and operates only on declarative specs; it never
reads or produces real client financial data.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from .config import ConfigError, load_document, validate_document
from .schemas import WORKPAPER_SCHEMA, load_schema

# The document types defined by the cpa-workpaper-spec vocabulary. These are the
# schema names (filename without the ``.schema.json`` suffix) published by that
# sibling repository; we reference them by name only.
SPEC_DOC_TYPES = (
    "engagement",
    "close-checklist",
    "tax-prep",
    "engagement-letter",
    "request-list-item",
)

# ``workpaper`` is this CLI's own bundled doc type (the default).
BUNDLED_DOC_TYPE = "workpaper"

KNOWN_DOC_TYPES = (BUNDLED_DOC_TYPE,) + SPEC_DOC_TYPES


@dataclass
class LintResult:
    """Outcome of linting a workpaper / CPA-document spec."""

    ok: bool
    doc_type: str = BUNDLED_DOC_TYPE
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

    return LintResult(
        ok=not errors, doc_type=BUNDLED_DOC_TYPE, errors=errors, warnings=warnings
    )


def _lint_bundled(spec: Dict[str, Any]) -> LintResult:
    """Lint against this package's bundled workpaper schema + semantic checks."""
    schema = load_schema(WORKPAPER_SCHEMA)
    structural = validate_document(spec, schema)
    if not structural.ok:
        return LintResult(
            ok=False, doc_type=BUNDLED_DOC_TYPE, errors=structural.errors
        )
    return _semantic_checks(spec)


def _load_spec_registry(spec_dir: Path):
    """Build an offline jsonschema registry from a cpa-workpaper-spec checkout.

    Every ``*.schema.json`` under ``spec_dir`` is registered under both its
    published ``$id`` and its bare filename, so the spec's cross-file ``$ref``
    graph resolves with no network access — exactly as the spec's own validator
    documents.
    """
    try:
        from referencing import Registry, Resource  # noqa: F401  (Resource used below)
    except ImportError as exc:  # pragma: no cover - optional dep guidance
        raise ConfigError(
            "validating cpa-workpaper-spec doc types needs the 'referencing' "
            "package (a jsonschema dependency); install jsonschema>=4.18"
        ) from exc

    schema_files = sorted(spec_dir.glob("*.schema.json"))
    if not schema_files:
        raise ConfigError(
            f"no *.schema.json files found under {spec_dir}; point --spec-dir "
            "at a cpa-workpaper-spec checkout's schema/<version>/ directory"
        )

    resources = []
    for path in schema_files:
        try:
            contents = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ConfigError(f"could not read spec schema {path}: {exc}") from exc
        resource = Resource.from_contents(contents)
        resources.append((path.name, contents, resource))

    registry = Registry()
    for filename, contents, resource in resources:
        # Register under the bare filename (used by relative $refs) ...
        registry = registry.with_resource(uri=filename, resource=resource)
        # ... and under the published $id when present.
        schema_id = contents.get("$id")
        if isinstance(schema_id, str):
            registry = registry.with_resource(uri=schema_id, resource=resource)
    return registry


def _lint_against_spec(
    spec: Dict[str, Any], doc_type: str, spec_dir: Path
) -> LintResult:
    """Validate ``spec`` against a named cpa-workpaper-spec schema."""
    try:
        from jsonschema import Draft202012Validator
    except ImportError as exc:  # pragma: no cover - jsonschema is a hard dep
        raise ConfigError("jsonschema is required for spec validation") from exc

    schema_path = spec_dir / f"{doc_type}.schema.json"
    if not schema_path.exists():
        available = ", ".join(
            sorted(p.name[: -len(".schema.json")] for p in spec_dir.glob("*.schema.json"))
        )
        raise ConfigError(
            f"doc-type '{doc_type}' not found in {spec_dir} "
            f"(available: {available or 'none'})"
        )

    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ConfigError(f"could not read {schema_path}: {exc}") from exc

    registry = _load_spec_registry(spec_dir)
    validator = Draft202012Validator(schema, registry=registry)
    errors = sorted(validator.iter_errors(spec), key=lambda e: list(e.absolute_path))
    messages = []
    for err in errors:
        location = "/".join(str(p) for p in err.absolute_path)
        where = f"{location}: " if location else ""
        messages.append(f"{where}{err.message}")
    return LintResult(ok=not messages, doc_type=doc_type, errors=messages)


def lint_spec(
    spec: Dict[str, Any],
    doc_type: str = BUNDLED_DOC_TYPE,
    spec_dir: Optional[Path] = None,
) -> LintResult:
    """Lint an already-parsed document.

    Args:
        spec: The parsed document.
        doc_type: ``workpaper`` (bundled schema) or one of the
            cpa-workpaper-spec doc types (``engagement``, ``close-checklist``,
            ``tax-prep``, ``engagement-letter``, ``request-list-item``).
        spec_dir: Required for spec doc types — a cpa-workpaper-spec checkout's
            ``schema/<version>/`` directory.
    """
    if doc_type not in KNOWN_DOC_TYPES:
        raise ConfigError(
            f"unknown doc-type '{doc_type}' (known: {', '.join(KNOWN_DOC_TYPES)})"
        )

    if doc_type == BUNDLED_DOC_TYPE:
        return _lint_bundled(spec)

    if spec_dir is None:
        raise ConfigError(
            f"doc-type '{doc_type}' is a cpa-workpaper-spec type; pass "
            "--spec-dir pointing at a cpa-workpaper-spec checkout's "
            "schema/<version>/ directory"
        )
    return _lint_against_spec(spec, doc_type, spec_dir)


def lint_file(
    path: Path,
    doc_type: str = BUNDLED_DOC_TYPE,
    spec_dir: Optional[Path] = None,
) -> LintResult:
    """Load and lint a workpaper / CPA-document file (JSON or YAML)."""
    document = load_document(path)
    return lint_spec(document, doc_type=doc_type, spec_dir=spec_dir)
