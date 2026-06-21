"""Sandbox/mock connectors for local smoke-testing.

These connectors are deliberately self-contained: they never open a network
socket and never touch real systems. They exist so a developer can exercise
the wiring of a workspace config end-to-end without credentials.
"""

from __future__ import annotations

from .base import Connector, ConnectorError, SmokeResult
from .registry import available_kinds, build_connector

__all__ = [
    "Connector",
    "ConnectorError",
    "SmokeResult",
    "available_kinds",
    "build_connector",
]
