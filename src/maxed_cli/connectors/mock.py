"""Built-in sandbox/mock connector drivers.

Every driver here is a pure in-process simulation built on synthetic fixtures.
They illustrate the connector contract without any product logic, network
access, or real client data.
"""

from __future__ import annotations

from typing import Any, Dict, List

from .base import Connector, SmokeResult

# --- Synthetic fixtures (clearly fake, deterministic) -----------------------

_FAKE_ACCOUNTS: List[Dict[str, Any]] = [
    {"code": "1000", "name": "Cash (sandbox)", "type": "asset"},
    {"code": "4000", "name": "Revenue (sandbox)", "type": "income"},
    {"code": "5000", "name": "Expenses (sandbox)", "type": "expense"},
]

_FAKE_DOCUMENTS: List[Dict[str, Any]] = [
    {"id": "doc-0001", "name": "sample-bank-statement.pdf", "bytes": 1024},
    {"id": "doc-0002", "name": "sample-receipt.png", "bytes": 512},
]

_FAKE_TAX_FORMS: List[Dict[str, Any]] = [
    {"form": "SAMPLE-1040", "year": 2025, "status": "draft"},
    {"form": "SAMPLE-1120", "year": 2025, "status": "draft"},
]


class EchoConnector(Connector):
    """Trivial connector that echoes its options back. Always succeeds."""

    kind = "echo"

    def smoke(self) -> SmokeResult:
        return self._ok("echo connector reachable", options=self.options)


class MockLedgerConnector(Connector):
    """Simulates a read-only ledger with a synthetic chart of accounts."""

    kind = "mock-ledger"

    def smoke(self) -> SmokeResult:
        accounts = list(_FAKE_ACCOUNTS)
        return self._ok(
            f"listed {len(accounts)} synthetic accounts",
            account_count=len(accounts),
            sample=accounts[0]["code"],
        )


class MockStorageConnector(Connector):
    """Simulates a document store with synthetic file metadata."""

    kind = "mock-storage"

    def smoke(self) -> SmokeResult:
        docs = list(_FAKE_DOCUMENTS)
        return self._ok(
            f"listed {len(docs)} synthetic documents",
            document_count=len(docs),
        )


class MockTaxFormsConnector(Connector):
    """Simulates a tax-forms catalog with synthetic, clearly-fake forms."""

    kind = "mock-tax-forms"

    def smoke(self) -> SmokeResult:
        forms = list(_FAKE_TAX_FORMS)
        return self._ok(
            f"listed {len(forms)} synthetic tax-form templates",
            form_count=len(forms),
        )
