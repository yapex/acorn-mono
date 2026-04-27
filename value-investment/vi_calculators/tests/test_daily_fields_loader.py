"""TDD tests: loader collects DAILY_FIELDS from calculator scripts.

Tests that:
1. load_calculators_from_path picks up DAILY_FIELDS
2. get_all_calculators includes daily_fields in spec
3. vi_list_calculators hook exposes daily_fields
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Ensure vi_calculators is importable
VI_CALC_DIR = Path(__file__).resolve().parent.parent / "vi_calculators"
if str(VI_CALC_DIR) not in sys.path:
    sys.path.insert(0, str(VI_CALC_DIR))

from vi_calculators import load_calculators_from_path, get_all_calculators, CalculatorEngine

CALC_DIR = Path(__file__).resolve().parent.parent.parent / "calculators"


class TestLoaderCollectsDailyFields:
    """load_calculators_from_path should extract DAILY_FIELDS."""

    def test_pe_percentile_has_daily_fields(self):
        """calc_pe_percentile declares DAILY_FIELDS = ["close"]."""
        calcs = load_calculators_from_path(CALC_DIR, "builtin")
        pe_calc = next((c for c in calcs if c["name"] == "pe_percentile"), None)
        assert pe_calc is not None, "pe_percentile calculator not found"
        assert pe_calc.get("daily_fields") == ["close"]

    def test_other_calculators_have_empty_daily_fields(self):
        """Calculators without DAILY_FIELDS should default to []."""
        calcs = load_calculators_from_path(CALC_DIR, "builtin")
        for calc in calcs:
            if calc["name"] == "pe_percentile":
                continue
            assert calc.get("daily_fields", []) == [], \
                f"{calc['name']} should have empty daily_fields"


class TestGetAllCalculatorsIncludesDailyFields:
    """get_all_calculators should include daily_fields."""

    def test_pe_percentile_in_all_calculators(self):
        all_calcs = get_all_calculators()
        pe_calc = next((c for c in all_calcs if c["name"] == "pe_percentile"), None)
        assert pe_calc is not None
        assert pe_calc["daily_fields"] == ["close"]


class TestListCalculatorsHookExposesDailyFields:
    """vi_list_calculators hook should expose daily_fields in spec."""

    def test_hook_spec_includes_daily_fields(self):
        engine = CalculatorEngine()
        calc_list = engine.vi_list_calculators()

        # Flatten if nested
        if calc_list and isinstance(calc_list[0], list):
            calc_list = calc_list[0]

        pe_calc = next((c for c in calc_list if c["name"] == "pe_percentile"), None)
        assert pe_calc is not None
        assert pe_calc["daily_fields"] == ["close"]
