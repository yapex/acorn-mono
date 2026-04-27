"""TDD tests for PE percentile calculator (calc_pe_percentile)

Tests cover:
1. Calculator spec (REQUIRED_FIELDS, DAILY_FIELDS, FORMAT_TYPES)
2. Pure calculation logic with synthetic data
3. Edge cases (negative EPS, missing data, single year)

Note: calculate(data) receives daily data as part of `data` dict,
injected by the framework (not via config).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import numpy as np
import pytest

# Ensure calculator can be imported
CALC_DIR = Path(__file__).resolve().parent.parent / "calculators"
if str(CALC_DIR) not in sys.path:
    sys.path.insert(0, str(CALC_DIR))

from calc_pe_percentile import calculate, REQUIRED_FIELDS, DAILY_FIELDS, FORMAT_TYPES


# ============================================================================
# 1. Calculator Spec Tests
# ============================================================================

class TestCalculatorSpec:
    """Calculator metadata declarations."""

    def test_required_fields_contains_basic_eps(self):
        assert "basic_eps" in REQUIRED_FIELDS

    def test_daily_fields_contains_close(self):
        assert "close" in DAILY_FIELDS

    def test_format_types_has_expected_keys(self):
        expected = {"pe_current", "pe_median", "pe_p25", "pe_p75", "pe_current_percentile"}
        assert set(FORMAT_TYPES.keys()) == expected

    def test_format_type_values(self):
        assert FORMAT_TYPES["pe_current_percentile"] == "percentage"
        assert FORMAT_TYPES["pe_current"] == "market"
        assert FORMAT_TYPES["pe_median"] == "market"


# ============================================================================
# 2. Calculation Logic Tests
# ============================================================================

def _make_daily_close(dates_prices: list[tuple[str, float]]) -> pd.DataFrame:
    """Helper: build daily close DataFrame."""
    return pd.DataFrame([
        {"date": pd.Timestamp(d), "close": p} for d, p in dates_prices
    ])


class TestPEPercentileCalculation:
    """Core PE percentile calculation with synthetic data."""

    def test_basic_calculation(self):
        """Simple case: 3 years of EPS, 6 trading days.

        EPS: 2022→10, 2023→12, 2024→15
        Prices (not adjusted):
          2023-01-01 → 120  (uses eps 2022=10  → PE=12)
          2023-06-01 → 150  (uses eps 2022=10  → PE=15)
          2024-01-01 → 150  (uses eps 2023=12  → PE=12.5)
          2024-06-01 → 180  (uses eps 2023=12  → PE=15)
          2025-01-01 → 180  (uses eps 2024=15  → PE=12)
          2025-04-01 → 210  (uses eps 2024=15  → PE=14)

        PE series: [12, 15, 12.5, 15, 12, 14]
        current_pe = 14
        sorted: [12, 12, 12.5, 14, 15, 15] → median = (12.5+14)/2=13.25
        """
        eps = pd.Series({2022: 10.0, 2023: 12.0, 2024: 15.0})
        close_df = _make_daily_close([
            ("2023-01-01", 120),
            ("2023-06-01", 150),
            ("2024-01-01", 150),
            ("2024-06-01", 180),
            ("2025-01-01", 180),
            ("2025-04-01", 210),
        ])

        result = calculate(data={"basic_eps": eps, "close": close_df})

        values = result["values"]
        assert len(values) == 5

        assert values["pe_current"] == pytest.approx(14.0, abs=0.01)
        assert values["pe_median"] == pytest.approx(13.25, abs=0.01)
        assert values["pe_p25"] == pytest.approx(12.125, abs=0.1)
        assert values["pe_p75"] == pytest.approx(14.75, abs=0.1)
        assert values["pe_current_percentile"] == pytest.approx(66.67, abs=1.0)

    def test_eps_availability_rule(self):
        """fiscal_year=N 的 EPS 从 N+1 年 1 月 1 日起可用.

        EPS: 2023→10
        - 2023-12-31: 无可用 EPS → 跳过
        - 2024-01-01: 可用 eps 2023=10 → PE = 100/10 = 10
        """
        eps = pd.Series({2023: 10.0})
        close_df = _make_daily_close([
            ("2023-06-01", 80),    # 2023 < 2024, no eps available → skipped
            ("2023-12-31", 100),   # 2023 < 2024, no eps available → skipped
            ("2024-01-01", 100),   # 2024 >= 2024, eps=10 → PE=10
            ("2024-06-01", 120),   # 2024 >= 2024, eps=10 → PE=12
        ])

        result = calculate(data={"basic_eps": eps, "close": close_df})

        values = result["values"]
        assert values["pe_current"] == pytest.approx(12.0)
        assert values["pe_median"] == pytest.approx(11.0)

    def test_current_pe_percentile_at_minimum(self):
        """Current PE is the lowest in history → percentile ~20."""
        eps = pd.Series({2022: 10.0, 2023: 10.0, 2024: 10.0})
        close_df = _make_daily_close([
            ("2023-01-01", 200),   # PE=20
            ("2023-06-01", 250),   # PE=25
            ("2024-01-01", 300),   # PE=30
            ("2024-06-01", 280),   # PE=28
            ("2025-01-01", 100),   # PE=10  (lowest)
        ])

        result = calculate(data={"basic_eps": eps, "close": close_df})

        values = result["values"]
        assert values["pe_current"] == pytest.approx(10.0)
        assert values["pe_current_percentile"] == pytest.approx(20.0, abs=1.0)

    def test_current_pe_percentile_at_maximum(self):
        """Current PE is the highest in history → percentile ~100."""
        eps = pd.Series({2022: 10.0, 2023: 10.0, 2024: 10.0})
        close_df = _make_daily_close([
            ("2023-01-01", 100),   # PE=10
            ("2023-06-01", 120),   # PE=12
            ("2024-01-01", 150),   # PE=15
            ("2024-06-01", 130),   # PE=13
            ("2025-01-01", 500),   # PE=50  (highest)
        ])

        result = calculate(data={"basic_eps": eps, "close": close_df})

        values = result["values"]
        assert values["pe_current"] == pytest.approx(50.0)
        assert values["pe_current_percentile"] == pytest.approx(100.0, abs=1.0)


# ============================================================================
# 3. Edge Cases
# ============================================================================

class TestPEPercentileEdgeCases:

    def test_no_close_data(self):
        """No close data in data dict → return empty result."""
        eps = pd.Series({2023: 10.0})
        result = calculate(data={"basic_eps": eps})
        assert len(result["values"]) == 0

    def test_empty_eps(self):
        """No EPS data → return empty result."""
        eps = pd.Series(dtype=float)
        close_df = _make_daily_close([("2024-01-01", 100)])
        result = calculate(data={"basic_eps": eps, "close": close_df})
        assert len(result["values"]) == 0

    def test_negative_eps_skipped(self):
        """Negative EPS should be skipped (no meaningful PE)."""
        eps = pd.Series({2022: -5.0, 2023: 10.0})
        close_df = _make_daily_close([
            ("2023-01-01", 100),   # eps 2022=-5 (negative, skip)
            ("2024-01-01", 100),   # eps 2023=10 → PE=10
        ])
        result = calculate(data={"basic_eps": eps, "close": close_df})
        values = result["values"]
        assert values["pe_current"] == pytest.approx(10.0)

    def test_zero_price_skipped(self):
        """Zero close price should be skipped."""
        eps = pd.Series({2023: 10.0})
        close_df = _make_daily_close([
            ("2024-01-01", 0),     # skip
            ("2024-06-01", 100),   # PE=10
        ])
        result = calculate(data={"basic_eps": eps, "close": close_df})
        assert result["values"]["pe_current"] == pytest.approx(10.0)

    def test_nan_eps_skipped(self):
        """NaN EPS values should be skipped."""
        eps = pd.Series({2022: float("nan"), 2023: 10.0})
        close_df = _make_daily_close([
            ("2023-01-01", 100),   # eps 2022=NaN → skip
            ("2024-01-01", 120),   # eps 2023=10 → PE=12
        ])
        result = calculate(data={"basic_eps": eps, "close": close_df})
        values = result["values"]
        assert values["pe_current"] == pytest.approx(12.0)

    def test_result_always_has_format_types(self):
        """Even empty results should include format_types."""
        eps = pd.Series(dtype=float)
        result = calculate(data={"basic_eps": eps})
        assert "format_types" in result
        assert "pe_current_percentile" in result["format_types"]
