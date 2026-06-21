"""Scaffold a local CPA-firm developer workspace from a config.

Given a validated workspace config, this creates the workspace root and its
sub-folders, drops a copy of the config inside, and writes a couple of
synthetic example fixtures so a developer has something to lint/smoke-test
immediately. Idempotent: re-running is safe.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List

DEFAULT_FOLDERS = ["workpapers", "configs", "fixtures", "exports"]

_EXAMPLE_WORKPAPER: Dict[str, Any] = {
    "spec_version": 1,
    "id": "WP-CASH-RECON",
    "title": "Cash reconciliation (example)",
    "period": "2025-Q2",
    "currency": "USD",
    "sections": [
        {
            "key": "balances",
            "label": "Balances",
            "line_items": [
                {"ref": "gl_balance", "label": "GL balance", "type": "amount"},
                {"ref": "bank_balance", "label": "Bank balance", "type": "amount"},
            ],
        },
        {
            "key": "reconciling_items",
            "label": "Reconciling items",
            "line_items": [
                {
                    "ref": "outstanding_checks",
                    "label": "Outstanding checks",
                    "type": "amount",
                    "required": False,
                }
            ],
        },
    ],
}


@dataclass
class ScaffoldResult:
    """Summary of what a scaffold run created or found already present."""

    root: Path
    created: List[Path] = field(default_factory=list)
    existed: List[Path] = field(default_factory=list)


def _ensure_dir(path: Path, result: ScaffoldResult) -> None:
    if path.exists():
        result.existed.append(path)
    else:
        path.mkdir(parents=True, exist_ok=True)
        result.created.append(path)


def _write_if_absent(path: Path, content: str, result: ScaffoldResult) -> None:
    if path.exists():
        result.existed.append(path)
        return
    path.write_text(content, encoding="utf-8")
    result.created.append(path)


def scaffold_workspace(config: Dict[str, Any], base_dir: Path) -> ScaffoldResult:
    """Create a workspace described by ``config`` under ``base_dir``.

    The workspace root comes from ``config['workspace']['root']`` and is
    resolved relative to ``base_dir`` when not absolute.

    Args:
        config: A workspace config that has already passed schema validation.
        base_dir: Directory the relative workspace root is resolved against.

    Returns:
        A :class:`ScaffoldResult` listing created and pre-existing paths.
    """
    workspace = config["workspace"]
    root = Path(workspace["root"])
    if not root.is_absolute():
        root = base_dir / root

    result = ScaffoldResult(root=root)
    _ensure_dir(root, result)

    folders = workspace.get("folders") or DEFAULT_FOLDERS
    for folder in folders:
        _ensure_dir(root / folder, result)

    # Drop a copy of the config so the workspace is self-describing.
    config_copy = root / "configs" / "workspace.json"
    config_copy.parent.mkdir(parents=True, exist_ok=True)
    _write_if_absent(
        config_copy,
        json.dumps(config, indent=2, sort_keys=True) + "\n",
        result,
    )

    # Seed a synthetic example workpaper for immediate linting.
    example = root / "workpapers" / "example.workpaper.json"
    example.parent.mkdir(parents=True, exist_ok=True)
    _write_if_absent(
        example,
        json.dumps(_EXAMPLE_WORKPAPER, indent=2) + "\n",
        result,
    )

    return result
