"""Tests for workpaper-spec linting."""

from __future__ import annotations

import copy

from maxed_cli.workpaper import lint_spec

VALID = {
    "spec_version": 1,
    "id": "WP-CASH-RECON",
    "title": "Cash reconciliation",
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
        }
    ],
}


def test_valid_spec_passes() -> None:
    result = lint_spec(copy.deepcopy(VALID))
    assert result.ok
    assert result.errors == []
    assert result.warnings == []


def test_missing_sections_fails() -> None:
    bad = copy.deepcopy(VALID)
    del bad["sections"]
    result = lint_spec(bad)
    assert not result.ok


def test_duplicate_section_key_detected() -> None:
    bad = copy.deepcopy(VALID)
    dup = copy.deepcopy(bad["sections"][0])
    dup["line_items"] = [{"ref": "other", "label": "Other", "type": "amount"}]
    bad["sections"].append(dup)
    result = lint_spec(bad)
    assert not result.ok
    assert any("duplicate section key" in e for e in result.errors)


def test_duplicate_ref_detected() -> None:
    bad = copy.deepcopy(VALID)
    bad["sections"].append(
        {
            "key": "more",
            "label": "More",
            "line_items": [
                {"ref": "gl_balance", "label": "Repeat", "type": "amount"}
            ],
        }
    )
    result = lint_spec(bad)
    assert not result.ok
    assert any("duplicate" in e and "ref" in e for e in result.errors)


def test_bad_id_pattern_fails() -> None:
    bad = copy.deepcopy(VALID)
    bad["id"] = "lower case id"
    assert not lint_spec(bad).ok


def test_invalid_line_item_type_fails() -> None:
    bad = copy.deepcopy(VALID)
    bad["sections"][0]["line_items"][0]["type"] = "currency"
    assert not lint_spec(bad).ok
