"""Scaffold a local CPA-firm developer workspace from a config.

``maxed init`` is the front door to the wider open-source suite. Given a
validated workspace config it creates the workspace tree, drops a self-
describing copy of the config, and — crucially — seeds a project that is
**pre-wired to use the sibling libraries**:

* a ``requirements.txt`` pinning ``accounting-adapters`` and
  ``statement-normalizer``;
* a runnable ``pipeline/import_transactions.py`` that imports those libraries
  and shows the canonical flow (normalize a statement → reconcile against a
  ledger adapter), guarded so it degrades gracefully if they are not installed;
* a synthetic bank-statement fixture the pipeline can chew on;
* a ``cpa-workpaper-spec`` ``close-checklist`` example so ``maxed
  lint-workpaper --doc-type close-checklist`` has something to validate; and
* the original simple example workpaper for the bundled linter.

Everything is synthetic and local. Idempotent: re-running is safe.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List

from .suite import PROJECT_REQUIREMENTS, SUITE

DEFAULT_FOLDERS = ["workpapers", "configs", "fixtures", "exports", "pipeline"]

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

# A synthetic, clearly-fake bank statement in the shape statement-normalizer's
# CSV parser understands (signed Amount column). No real account data.
_EXAMPLE_STATEMENT_CSV = (
    "Transaction Date,Description,Amount\n"
    "2025-04-01,OPENING BALANCE,0.00\n"
    "2025-04-03,ACME OFFICE SUPPLY,(120.55)\n"
    "2025-04-09,CLIENT PAYMENT - INV 1009,2500.00\n"
    "2025-04-15,CLOUD HOSTING SUBSCRIPTION,(89.00)\n"
    "2025-04-22,BANK SERVICE FEE,(12.00)\n"
)

# A minimal cpa-workpaper-spec close-checklist document (v0.1 shape). This is a
# synthetic example targeting the published vocabulary; the normative schema
# lives in the cpa-workpaper-spec repository.
_EXAMPLE_CLOSE_CHECKLIST: Dict[str, Any] = {
    "specVersion": "0.1",
    "id": "close_2025_04_example",
    "engagementId": "eng_example_0001",
    "period": {"label": "2025-04", "start": "2025-04-01", "end": "2025-04-30"},
    "status": "in_progress",
    "tasks": [
        {
            "id": "t_bank",
            "name": "Reconcile operating bank account",
            "category": "reconciliation",
            "status": "in_progress",
        },
        {
            "id": "t_cc",
            "name": "Reconcile credit card",
            "category": "reconciliation",
            "status": "blocked",
            "openItemIds": ["oi_acme"],
        },
    ],
    "openItems": [
        {
            "id": "oi_acme",
            "question": "What is the 2025-04-03 ACME Office Supply charge for?",
            "status": "awaiting_response",
            "directedTo": "client",
        }
    ],
}


def _pipeline_script(config: Dict[str, Any]) -> str:
    """Render the pre-wired example pipeline that uses the sibling libraries."""
    firm = config.get("firm", {}).get("name", "your firm")
    aa = SUITE["accounting-adapters"]
    sn = SUITE["statement-normalizer"]
    return f'''#!/usr/bin/env python3
"""Example import pipeline for {firm} — scaffolded by `maxed init`.

This is a *starting point*, pre-wired to the open-source suite:

  - {sn.name}: {sn.summary}
      {sn.repo}
  - {aa.name}: {aa.summary}
      {aa.repo}

Install the suite, then run this file:

    pip install -r ../requirements.txt
    python import_transactions.py

It deliberately uses only the public APIs of those libraries. Swap the
synthetic fixture / sandbox adapter for real inputs when you are ready.
"""
from __future__ import annotations

from pathlib import Path

HERE = Path(__file__).resolve().parent
STATEMENT = HERE.parent / "fixtures" / "statement.csv"


def main() -> int:
    try:
        from statement_normalizer import normalize_file
    except ImportError:
        print(
            "statement-normalizer is not installed. Run:\\n"
            "    pip install -r ../requirements.txt"
        )
        return 1

    # 1. Normalize a messy bank statement into clean transaction records.
    statement = normalize_file(str(STATEMENT))
    print(f"normalized {{len(statement.transactions)}} transactions "
          f"({{statement.currency}})")
    for txn in statement.transactions:
        print(f"  {{txn.date}}  {{txn.amount:>10}}  {{txn.description}}")

    # 2. (Optional) Pull the chart of accounts from a ledger via
    #    accounting-adapters to categorize against. You supply credentials.
    #
    #    from accounting_adapters import QuickBooksAdapter
    #    qbo = QuickBooksAdapter(realm_id="...", access_token="...")
    #    accounts = qbo.all_accounts()
    #
    # The two libraries share no code with each other or with this CLI; they
    # just compose cleanly because each speaks a normalized model.
    print("\\nNext: wire accounting-adapters to categorize/reconcile these.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''


def _project_readme(config: Dict[str, Any]) -> str:
    firm = config.get("firm", {}).get("name", "Your firm")
    lines = [
        f"# {firm} — accounting-tech workspace",
        "",
        "Scaffolded by [`maxed`](https://github.com/maxed-oss/maxed-cli). This",
        "project is pre-wired to the open-source accounting-tech suite.",
        "",
        "## Layout",
        "",
        "```",
        "configs/      self-describing copy of the workspace config",
        "fixtures/     synthetic inputs (e.g. statement.csv)",
        "pipeline/     runnable example using the suite libraries",
        "workpapers/   workpaper + cpa-workpaper-spec example documents",
        "exports/      pipeline outputs land here",
        "```",
        "",
        "## Quick start",
        "",
        "```bash",
        "pip install -r requirements.txt",
        "python pipeline/import_transactions.py",
        "maxed lint-workpaper workpapers/example.workpaper.json",
        "```",
        "",
        "## The suite",
        "",
    ]
    for pkg in SUITE.values():
        lines.append(f"- **{pkg.name}** — {pkg.summary} <{pkg.repo}>")
    lines.append("")
    return "\n".join(lines)


def _requirements_txt() -> str:
    header = [
        "# Pre-wired dependencies for this maxed workspace.",
        "# These are the open-source suite libraries the example pipeline uses.",
        "",
    ]
    return "\n".join(header + list(PROJECT_REQUIREMENTS)) + "\n"


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
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    result.created.append(path)


def scaffold_workspace(config: Dict[str, Any], base_dir: Path) -> ScaffoldResult:
    """Create a suite-wired workspace described by ``config`` under ``base_dir``.

    The workspace root comes from ``config['workspace']['root']`` and is
    resolved relative to ``base_dir`` when not absolute.

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

    # Self-describing copy of the config.
    _write_if_absent(
        root / "configs" / "workspace.json",
        json.dumps(config, indent=2, sort_keys=True) + "\n",
        result,
    )

    # Synthetic example workpaper for the bundled linter.
    _write_if_absent(
        root / "workpapers" / "example.workpaper.json",
        json.dumps(_EXAMPLE_WORKPAPER, indent=2) + "\n",
        result,
    )

    # cpa-workpaper-spec close-checklist example (targets the published spec).
    _write_if_absent(
        root / "workpapers" / "example.close-checklist.json",
        json.dumps(_EXAMPLE_CLOSE_CHECKLIST, indent=2) + "\n",
        result,
    )

    # Pre-wired suite integration: requirements, a synthetic statement, an
    # example pipeline, and a project README.
    _write_if_absent(root / "requirements.txt", _requirements_txt(), result)
    _write_if_absent(root / "fixtures" / "statement.csv", _EXAMPLE_STATEMENT_CSV, result)
    _write_if_absent(
        root / "pipeline" / "import_transactions.py",
        _pipeline_script(config),
        result,
    )
    _write_if_absent(root / "README.md", _project_readme(config), result)

    return result
