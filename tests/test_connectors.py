"""Tests for the sandbox/mock connector harness."""

from __future__ import annotations

import pytest

from maxed_cli.connectors import available_kinds, build_connector
from maxed_cli.connectors.base import ConnectorError


def test_available_kinds_stable() -> None:
    kinds = available_kinds()
    assert kinds == sorted(kinds)
    assert {"mock-ledger", "mock-storage", "mock-tax-forms", "echo"} <= set(kinds)


@pytest.mark.parametrize("kind", ["mock-ledger", "mock-storage", "mock-tax-forms", "echo"])
def test_each_connector_smoke_passes(kind: str) -> None:
    connector = build_connector(name=f"t-{kind}", kind=kind)
    result = connector.smoke()
    assert result.ok
    assert result.kind == kind
    assert result.detail


def test_echo_echoes_options() -> None:
    connector = build_connector(name="ping", kind="echo", options={"note": "hi"})
    result = connector.smoke()
    assert result.ok
    assert result.data["options"] == {"note": "hi"}


def test_ledger_reports_account_count() -> None:
    result = build_connector(name="l", kind="mock-ledger").smoke()
    assert result.data["account_count"] >= 1


def test_unknown_kind_raises() -> None:
    with pytest.raises(ConnectorError):
        build_connector(name="x", kind="does-not-exist")
