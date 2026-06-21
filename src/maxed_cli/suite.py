"""Knowledge of the sibling open-source packages this CLI is the front door to.

``maxed-cli`` is the on-ramp to a small suite of independent, firm-agnostic
open-source libraries. This module records — *by name and published interface
only* — how a scaffolded project wires those libraries together. It deliberately
contains **no copied code** from the sibling repositories; it only references
them the way any downstream consumer would (PyPI name + public entry points).

Sibling packages referenced:

* ``accounting-adapters`` — one normalized read interface over public
  accounting APIs (QuickBooks Online, Xero, Bill.com, TaxDome, Plaid).
* ``statement-normalizer`` — deterministic bank/credit-card statement parsing
  into normalized transaction JSON (CSV / OFX / text).
* ``cpa-workpaper-spec`` — an open, versioned JSON-Schema vocabulary for the
  common units of CPA work (engagement, close-checklist, tax-prep, …).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class SuitePackage:
    """A sibling open-source package this CLI helps you adopt."""

    name: str
    pypi: str
    summary: str
    repo: str


SUITE: Dict[str, SuitePackage] = {
    "accounting-adapters": SuitePackage(
        name="accounting-adapters",
        pypi="accounting-adapters",
        summary=(
            "One normalized read interface over public accounting APIs "
            "(QuickBooks Online, Xero, Bill.com, TaxDome, Plaid)."
        ),
        repo="https://github.com/maxed-oss/accounting-adapters",
    ),
    "statement-normalizer": SuitePackage(
        name="statement-normalizer",
        pypi="statement-normalizer",
        summary=(
            "Deterministic bank/credit-card statement parsing into normalized "
            "transaction JSON (CSV / OFX / text)."
        ),
        repo="https://github.com/maxed-oss/statement-normalizer",
    ),
    "cpa-workpaper-spec": SuitePackage(
        name="cpa-workpaper-spec",
        pypi="cpa-workpaper-spec",
        summary=(
            "An open, versioned JSON-Schema vocabulary for the common units of "
            "CPA work (engagement, close-checklist, tax-prep, request lists)."
        ),
        repo="https://github.com/maxed-oss/cpa-workpaper-spec",
    ),
}

# Pinned, conservative version floors a generated project depends on. These are
# requirement *specifiers* only — installing them is the user's choice.
PROJECT_REQUIREMENTS: List[str] = [
    "accounting-adapters>=0.1,<1.0",
    "statement-normalizer>=0.1,<1.0",
]


def suite_as_dict() -> List[Dict[str, str]]:
    """Return the suite catalog as JSON-serializable records."""
    return [
        {
            "name": pkg.name,
            "pypi": pkg.pypi,
            "summary": pkg.summary,
            "repo": pkg.repo,
        }
        for pkg in SUITE.values()
    ]
