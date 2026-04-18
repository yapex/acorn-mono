"""Tests for BaseDataProvider years filtering.

BUG REPRODUCTION: fetch_indicators should filter results to N years
but currently returns all historical data because _fetch_indicators_impl
ignores the start_year/end_year parameters.

Expected behavior:
- fetch_indicators(end_year=2024, years=5) should return 5 years of data (2020-2024)
- fetch_financials(end_year=2024, years=5) should return 5 years of data (2020-2024)
- fetch_market(end_year=2024, years=5) should return 5 years of data (2020-2024)

Actual behavior (BUG):
- fetch_indicators returns ALL historical years (e.g., 1998-2024 = 27 years)
- fetch_financials works correctly (internal filtering in _fetch_all_financials)
- fetch_market works correctly (has explicit year filtering logic)
"""
from __future__ import annotations

import pandas as pd
import pytest
from unittest.mock import patch, MagicMock

from vi_core.base_provider import BaseDataProvider
from vi_fields_extension import StandardFields


class FakeProvider(BaseDataProvider):
    """Fake provider that returns known multi-year data for testing."""

    MARKET_CODE = "TEST"

    FIELD_MAPPINGS = {
        "indicators": {
            "fake_roe": "roe",
            "fake_gross_margin": "gross_margin",
        },
        "financials": {
            "fake_revenue": "total_revenue",
        },
    }

    def _normalize_symbol(self, symbol: str) -> str:
        return symbol

    def _fetch_all_financials(self, symbol, start_year, end_year, fields):
        # Simulates fetching full history, then being filtered
        years = list(range(1998, 2025))
        data = {
            "fiscal_year": years,
            "total_revenue": [100 * (i + 1) for i in range(len(years))],
        }
        return pd.DataFrame(data)

    def _fetch_indicators_impl(self, symbol, start_year, end_year):
        # BUG: This implementation ignores start_year/end_year and returns ALL years
        years = list(range(1998, 2025))  # 27 years of data
        data = {
            "fiscal_year": years,
            "roe": [30.0 + i * 0.1 for i in range(len(years))],
            "gross_margin": [90.0 + i * 0.05 for i in range(len(years))],
        }
        return pd.DataFrame(data)

    def _fetch_market_impl(self, symbol, end_year=None, years=10):
        # Returns only one row (market data is typically single-point)
        return pd.DataFrame({
            "fiscal_year": [end_year],
            "market_cap": [5000],
        })


class TestFetchIndicatorsYearsFiltering:
    """Test that fetch_indicators filters to the requested number of years."""

    def setup_method(self):
        self.provider = FakeProvider(cache=None)

    def test_fetch_indicators_filters_to_requested_years(self):
        """fetch_indicators(end_year=2024, years=5) should return only 5 years."""
        df = self.provider.fetch_indicators(
            symbol="TEST",
            fields={"roe", "gross_margin"},
            end_year=2024,
            years=5,
        )

        assert df is not None, "Should return data"
        # Extract fiscal years from the returned data
        result_years = sorted(df[StandardFields.fiscal_year].tolist())
        expected_years = [2020, 2021, 2022, 2023, 2024]

        assert result_years == expected_years, (
            f"Expected years {expected_years}, got {result_years}. "
            f"fetch_indicators should filter to N years, but returned {len(result_years)} years."
        )

    def test_fetch_indicators_returns_only_requested_years_not_all(self):
        """Regression: ensure we don't return ALL historical years."""
        df = self.provider.fetch_indicators(
            symbol="TEST",
            fields={"roe"},
            end_year=2024,
            years=5,
        )

        result_year_count = len(df[StandardFields.fiscal_year].unique())
        assert result_year_count == 5, (
            f"Expected 5 years, got {result_year_count}. "
            f"BUG: fetch_indicators returns all historical years instead of filtering."
        )

    def test_fetch_indicators_10_years(self):
        """Requesting 10 years should return exactly 10 years."""
        df = self.provider.fetch_indicators(
            symbol="TEST",
            fields={"roe"},
            end_year=2024,
            years=10,
        )

        result_years = sorted(df[StandardFields.fiscal_year].tolist())
        expected_years = list(range(2015, 2025))
        assert result_years == expected_years


class TestFetchFinancialsYearsFiltering:
    """Test that fetch_financials filters to the requested number of years (baseline)."""

    def setup_method(self):
        self.provider = FakeProvider(cache=None)

    def test_fetch_financials_filters_to_requested_years(self):
        """fetch_financials(end_year=2024, years=5) should return only 5 years."""
        df = self.provider.fetch_financials(
            symbol="TEST",
            fields={"total_revenue"},
            end_year=2024,
            years=5,
        )

        assert df is not None
        result_years = sorted(df[StandardFields.fiscal_year].tolist())
        expected_years = [2020, 2021, 2022, 2023, 2024]

        assert result_years == expected_years, (
            f"Expected years {expected_years}, got {result_years}"
        )


class TestFetchMarketYearsFiltering:
    """Test that fetch_market filters to the requested number of years (baseline)."""

    def setup_method(self):
        self.provider = FakeProvider(cache=None)

    def test_fetch_market_respects_years_parameter(self):
        """fetch_market should return data for the correct fiscal years."""
        # Note: market data is typically single-point, so we mainly verify it doesn't crash
        df = self.provider.fetch_market(
            symbol="TEST",
            fields={"market_cap"},
            end_year=2024,
            years=5,
        )

        assert df is not None
        assert len(df) == 1
        assert df[StandardFields.fiscal_year].iloc[0] == 2024
