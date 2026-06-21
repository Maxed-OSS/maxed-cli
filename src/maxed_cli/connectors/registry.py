"""Registry mapping connector ``kind`` values to driver classes."""

from __future__ import annotations

from typing import Any, Dict, List, Type

from .base import Connector, ConnectorError
from .mock import (
    EchoConnector,
    MockLedgerConnector,
    MockStorageConnector,
    MockTaxFormsConnector,
)

_REGISTRY: Dict[str, Type[Connector]] = {
    EchoConnector.kind: EchoConnector,
    MockLedgerConnector.kind: MockLedgerConnector,
    MockStorageConnector.kind: MockStorageConnector,
    MockTaxFormsConnector.kind: MockTaxFormsConnector,
}


def available_kinds() -> List[str]:
    """Return the sorted list of registered connector kinds."""
    return sorted(_REGISTRY)


def build_connector(
    name: str, kind: str, options: Dict[str, Any] | None = None
) -> Connector:
    """Instantiate a connector by kind.

    Raises:
        ConnectorError: If the kind is unknown.
    """
    driver = _REGISTRY.get(kind)
    if driver is None:
        known = ", ".join(available_kinds())
        raise ConnectorError(f"unknown connector kind '{kind}' (known: {known})")
    return driver(name=name, options=options)
