"""TDD tests: _query fetches daily data and injects into calculator data.

Tests that:
1. pe_percentile calculator spec includes daily_fields
2. _query collects daily_fields, fetches historical data, injects into data
3. End-to-end: pe_percentile produces results through _query
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pluggy
import pytest

# Add src paths
ROOT = Path(__file__).resolve().parent.parent
for src in [
    ROOT / "vi_core" / "src",
    ROOT / "vi_fields_extension" / "src",
    ROOT / "vi_fields_ifrs" / "src",
    ROOT / "provider_market_a" / "src",
    ROOT / "provider_market_hk" / "src",
    ROOT / "provider_market_us" / "src",
    ROOT / "vi_calculators",
    ROOT / "calculators",
]:
    if str(src) not in sys.path and src.exists():
        sys.path.insert(0, str(src))

from vi_core.spec import ValueInvestmentSpecs, vi_hookimpl
from vi_core.plugin import ViCorePlugin


# ============================================================================
# Mock Provider: returns basic_eps annual data + historical close
# ============================================================================

class MockProvider:
    """Mock provider that responds to A market."""

    @vi_hookimpl
    def vi_markets(self):
        return ["A"]

    @vi_hookimpl
    def vi_supported_fields(self):
        return ["basic_eps"]

    @vi_hookimpl
    def vi_fields(self):
        from vi_fields_extension import StandardFields
        return {
            "source": "mock",
            "fields": {
                StandardFields.basic_eps: {"description": "基本每股收益"},
            },
            "format_types": {},
        }

    @vi_hookimpl
    def vi_provide_items(self, items, symbol, market, end_year, years):
        if market != "A":
            return None
        if "basic_eps" not in items:
            return None

        # Return 3 years of EPS data
        return pd.DataFrame({
            "fiscal_year": [2022, 2023, 2024],
            "basic_eps": [10.0, 12.0, 15.0],
        })

    @vi_hookimpl
    def vi_fetch_historical(self, symbol, start_date, end_date, adjust):
        """Return mock daily close prices (not adjusted)."""
        return pd.DataFrame({
            "date": pd.to_datetime([
                "2023-01-01", "2023-06-01",
                "2024-01-01", "2024-06-01",
                "2025-01-01", "2025-04-01",
            ]),
            "close": [120.0, 150.0, 150.0, 180.0, 180.0, 210.0],
        })


def _setup_pm():
    """Create a pluggy PluginManager with mock provider + vi_core + calculators."""
    from vi_calculators import CalculatorEngine

    pm = pluggy.PluginManager("value_investment")
    pm.add_hookspecs(ValueInvestmentSpecs)

    core = ViCorePlugin()
    pm.register(core, name="vi_core")
    core.set_plugin_manager(pm)

    pm.register(MockProvider(), name="mock_provider")
    pm.register(CalculatorEngine(), name="calculators")

    return pm, core


# ============================================================================
# Tests
# ============================================================================

class TestQueryCollectsDailyFields:
    """_query should collect daily_fields from calculator specs."""

    def test_pe_percentile_daily_fields_in_calc_list(self):
        """pe_percentile calculator spec should include daily_fields."""
        from vi_calculators import CalculatorEngine
        engine = CalculatorEngine()
        calc_list = engine.vi_list_calculators()
        if isinstance(calc_list[0], list):
            calc_list = calc_list[0]

        pe_calc = next(c for c in calc_list if c["name"] == "pe_percentile")
        assert pe_calc["daily_fields"] == ["close"]


class TestQueryEndToEnd:
    """End-to-end: pe_percentile calculator produces correct results."""

    def test_pe_percentile_e2e(self):
        """Full pipeline: _query → fetch eps + daily close → calculate → return."""
        pm, core = _setup_pm()

        result = core._handle("query", {
            "symbol": "600519",
            "items": "pe_percentile",
        })

        assert result["success"] is True, f"Query failed: {result}"

        data = result["data"]["data"]

        # pe_percentile 的多指标结果被展开为 {str_key: float_val}
        assert "pe_percentile" in data, f"Expected pe_percentile, got keys: {list(data.keys())}"

        pe_result = data["pe_percentile"]
        assert "pe_current" in pe_result, f"Expected pe_current in {list(pe_result.keys())}"
        assert "pe_median" in pe_result
        assert "pe_current_percentile" in pe_result

        # EPS: 2022→10, 2023→12, 2024→15
        # 最后一天: 2025-04-01 → 210, uses eps 2024=15, PE=14
        assert pe_result["pe_current"] == pytest.approx(14.0, abs=0.01)

    def test_pe_percentile_also_returns_basic_eps(self):
        """When pe_percentile is requested, its required field basic_eps
        should also be fetched and returned."""
        pm, core = _setup_pm()

        result = core._handle("query", {
            "symbol": "600519",
            "items": "pe_percentile",
        })

        assert result["success"] is True
        data = result["data"]["data"]
        assert "basic_eps" in data
