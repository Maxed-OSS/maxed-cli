"""Connector base types for the local smoke-test harness."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict


class ConnectorError(Exception):
    """Raised when a connector cannot be built or run."""


@dataclass
class SmokeResult:
    """Result of a single connector smoke-test."""

    name: str
    kind: str
    ok: bool
    detail: str
    data: Dict[str, Any] = field(default_factory=dict)


class Connector:
    """Base class for sandbox/mock connectors.

    Subclasses implement :meth:`smoke`, returning a :class:`SmokeResult`.
    A connector is constructed with a local label and a free-form options
    mapping (no secrets). Connectors are pure in-process simulations.
    """

    #: Stable driver identifier, set by subclasses.
    kind: str = "base"

    def __init__(self, name: str, options: Dict[str, Any] | None = None) -> None:
        self.name = name
        self.options: Dict[str, Any] = dict(options or {})

    def smoke(self) -> SmokeResult:  # pragma: no cover - abstract
        """Run a self-contained smoke-test and report the outcome."""
        raise NotImplementedError

    def _ok(self, detail: str, **data: Any) -> SmokeResult:
        return SmokeResult(self.name, self.kind, True, detail, dict(data))

    def _fail(self, detail: str, **data: Any) -> SmokeResult:
        return SmokeResult(self.name, self.kind, False, detail, dict(data))
