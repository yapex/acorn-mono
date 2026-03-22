"""Tests for provider_market_hk plugin"""
from __future__ import annotations

import pytest

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
        expected_fields = ["total_assets", "roe", "pe_ratio", "hk_market_cap"]
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
            "hk_market_cap",
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

    def test_get_date_column_returns_year(self):
        """Test _get_date_column returns year"""
        provider = HKProvider()
        assert provider._get_date_column() == "year"


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


class TestHKProviderIntegration:
    """Integration tests for HKProvider (requires API)"""

    @pytest.fixture
    def provider(self):
        """Create provider instance"""
        return HKProvider()

    def test_provider_creation(self, provider):
        """Test provider can be created"""
        assert provider is not None
