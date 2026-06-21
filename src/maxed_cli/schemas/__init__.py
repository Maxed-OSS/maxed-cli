"""Bundled JSON Schemas for maxed-cli.

Schemas are loaded as package data so they ship inside the installed wheel.
"""

from __future__ import annotations

import json
from importlib import resources
from typing import Any, Dict

CONFIG_SCHEMA = "config.schema.json"
WORKPAPER_SCHEMA = "workpaper.schema.json"


def load_schema(name: str) -> Dict[str, Any]:
    """Load a bundled JSON Schema by file name.

    Args:
        name: One of CONFIG_SCHEMA or WORKPAPER_SCHEMA.

    Returns:
        The parsed schema as a dict.
    """
    text = resources.files(__package__).joinpath(name).read_text(encoding="utf-8")
    return json.loads(text)
