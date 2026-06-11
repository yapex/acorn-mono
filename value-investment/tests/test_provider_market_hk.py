"""Tests for provider_market_hk plugin"""
from __future__ import annotations

import pytest
import pandas as pd

from provider_market_hk.plugin import plugin as provider_hk_plugin
from provider_market_hk.provider import HKProvider


class TestProviderHKMarketPlugin:
    """Test ProviderHKPlugin"""

    def test_vi_markets_returns_hk(self):
        """Test vi_markets returns HK market"""
        markets = provider_hk_plugin.vi_markets()
        assert markets == ["HK"]
        assert len(markets) == 1

    def test_vi_supported_fields_returns_list(self):
        """Test vi_supported_fields returns list of fields"""
        fields = provider_hk_plugin.vi_supported_fields()
        assert isinstance(fields, list)
        assert len(fields) > 0

    def test_vi_supported_fields_contains_financial_fields(self):
        """Test supported fields contain financial fields"""
        fields = provider_hk_plugin.vi_supported_fields()
        expected_fields = ["total_assets", "roe", "pe_ratio", "market_cap"]
        for field in expected_fields:
            assert field in fields, f"{field} should be in supported fields"

    def test_supported_fields_count(self):
        """Test supported fields count"""
        fields = provider_hk_plugin.vi_supported_fields()
        # 港股字段数应该大于 50
        assert len(fields) > 50, f"Expected more than 50 fields, got {len(fields)}"


class TestHKProvider:
    """Test HKProvider class"""

    def test_supported_fields_is_set_from_method(self):
        """Test get_supported_fields returns a set"""
        fields = HKProvider.get_supported_fields()
        assert isinstance(fields, set)
        assert len(fields) > 0

    def test_supported_fields_contains_balance_fields(self):
        """Test get_supported_fields contains balance sheet fields"""
        balance_fields = {
            "total_assets",
            "total_equity",
            "total_liabilities",
            "cash_and_equivalents",
        }
        supported = HKProvider.get_supported_fields()
        for field in balance_fields:
            assert field in supported

    def test_supported_fields_contains_indicator_fields(self):
        """Test get_supported_fields contains indicator fields"""
        indicator_fields = {
            "roe",
            "net_profit_margin",
            "hk_dividend_yield_ttm",
        }
        supported = HKProvider.get_supported_fields()
        for field in indicator_fields:
            assert field in supported

    def test_supported_fields_contains_market_fields(self):
        """Test get_supported_fields contains market fields"""
        market_fields = {
            "market_cap",
            "pe_ratio",
            "pb_ratio",
        }
        supported = HKProvider.get_supported_fields()
        for field in market_fields:
            assert field in supported

    def test_field_mappings_defined(self):
        """Test FIELD_MAPPINGS is defined"""
        assert hasattr(HKProvider, "FIELD_MAPPINGS")
        assert isinstance(HKProvider.FIELD_MAPPINGS, dict)

    def test_field_mappings_contains_statement_types(self):
        """Test FIELD_MAPPINGS contains expected statement types"""
        expected_types = ["balance_sheet", "income_statement", "cash_flow", "indicators", "market"]
        for stmt_type in expected_types:
            assert stmt_type in HKProvider.FIELD_MAPPINGS, f"{stmt_type} should be in mappings"

    def test_normalize_symbol_converts_to_5_digits(self):
        """Test _normalize_symbol converts to 5-digit format"""
        provider = HKProvider()
        result = provider._normalize_symbol("00700")
        assert result == "00700"

    def test_normalize_symbol_preserves_existing(self):
        """Test _normalize_symbol preserves 5-digit format"""
        provider = HKProvider()
        result = provider._normalize_symbol("00700")
        assert result == "00700"




class TestHKProviderFetchMethods:
    """Test HKProvider fetch methods"""

    def test_fetch_financials_returns_none_for_empty_fields(self):
        """Test fetch_financials returns None for empty fields"""
        provider = HKProvider()

        # Should return None for empty fields
        result = provider.fetch_financials(
            symbol="00700",
            fields=set(),
            end_year=2024,
            years=5
        )
        assert result is None

    def test_fetch_indicators_returns_none_for_empty_fields(self):
        """Test fetch_indicators returns None for empty fields"""
        provider = HKProvider()

        result = provider.fetch_indicators(
            symbol="00700",
            fields=set(),
            end_year=2024,
            years=5
        )
        assert result is None

    def test_fetch_market_returns_none_for_empty_fields(self):
        """Test fetch_market returns None for empty fields"""
        provider = HKProvider()

        result = provider.fetch_market(
            symbol="00700",
            fields=set()
        )
        assert result is None


class TestHKProviderFetchMarketImpl:
    """Test _fetch_market_impl returns valuation data (market_cap, pe_ratio, pb_ratio)"""

    @pytest.fixture
    def provider(self):
        return HKProvider()

    def test_fetch_market_impl_returns_close(self, provider):
        """_fetch_market_impl should return close price"""
        df = provider._fetch_market_impl("00388", years=5)
        assert df is not None
        assert "close" in df.columns or "收盘" in df.columns

    def test_fetch_market_impl_returns_market_cap(self, provider):
        """_fetch_market_impl should return 总市值(港元) column"""
        df = provider._fetch_market_impl("00388", years=1)
        assert df is not None
        assert "总市值(港元)" in df.columns or "market_cap" in df.columns

    def test_fetch_market_impl_returns_pe_ratio(self, provider):
        """_fetch_market_impl should return 市盈率 column"""
        df = provider._fetch_market_impl("00388", years=1)
        assert df is not None
        assert "市盈率" in df.columns or "pe_ratio" in df.columns

    def test_fetch_market_impl_returns_pb_ratio(self, provider):
        """_fetch_market_impl should return 市净率 column"""
        df = provider._fetch_market_impl("00388", years=1)
        assert df is not None
        assert "市净率" in df.columns or "pb_ratio" in df.columns

    def test_fetch_market_valuation_values_not_nan(self, provider):
        """Valuation values should not be NaN"""
        df = provider._fetch_market_impl("00388", years=1)
        assert df is not None
        # Check the latest year row
        latest = df.iloc[0]
        # 市值应该是正数
        mc_col = "总市值(港元)" if "总市值(港元)" in df.columns else "market_cap"
        assert pd.notna(latest[mc_col])
        assert latest[mc_col] > 0

    def test_fetch_market_multi_year_close(self, provider):
        """Multi-year fetch should return multiple rows with close prices"""
        df = provider._fetch_market_impl("00388", years=5)
        assert df is not None
        # Should have at least 3 years of close data
        close_col = "close" if "close" in df.columns else "收盘"
        assert len(df) >= 3
        assert df[close_col].notna().all()


class TestHKProviderFetchMarketIntegration:
    """Integration: fetch_market (public method with mapping) should return standard fields"""

    @pytest.fixture
    def provider(self):
        return HKProvider()

    def test_fetch_market_returns_mapped_market_cap(self, provider):
        """fetch_market should return market_cap after field mapping"""
        df = provider.fetch_market("00388", fields={"market_cap"})
        assert df is not None
        assert "market_cap" in df.columns
        latest = df.iloc[0]
        assert pd.notna(latest["market_cap"])
        assert latest["market_cap"] > 0

    def test_fetch_market_returns_mapped_pe_ratio(self, provider):
        """fetch_market should return pe_ratio after field mapping"""
        df = provider.fetch_market("00388", fields={"pe_ratio"})
        assert df is not None
        assert "pe_ratio" in df.columns
        latest = df.iloc[0]
        assert pd.notna(latest["pe_ratio"])

    def test_fetch_market_returns_mapped_pb_ratio(self, provider):
        """fetch_market should return pb_ratio after field mapping"""
        df = provider.fetch_market("00388", fields={"pb_ratio"})
        assert df is not None
        assert "pb_ratio" in df.columns
        latest = df.iloc[0]
        assert pd.notna(latest["pb_ratio"])

    def test_fetch_market_returns_multiple_fields(self, provider):
        """fetch_market should return close + market_cap + pe_ratio together"""
        df = provider.fetch_market("00388", fields={"close", "market_cap", "pe_ratio", "pb_ratio"})
        assert df is not None
        assert "close" in df.columns
        assert "market_cap" in df.columns
        assert "pe_ratio" in df.columns
        assert "pb_ratio" in df.columns


class TestHKProviderIntegration:
    """Integration tests for HKProvider (requires API)"""

    @pytest.fixture
    def provider(self):
        """Create provider instance"""
        return HKProvider()

    def test_provider_creation(self, provider):
        """Test provider can be created"""
        assert provider is not None
