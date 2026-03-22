"""Tests for provider_market_us plugin"""
from __future__ import annotations

import pytest

from provider_market_us.plugin import plugin as provider_us_plugin
from provider_market_us.provider import USProvider


class TestProviderUSMarketPlugin:
    """Test ProviderUSPlugin"""

    def test_vi_markets_returns_us(self):
        """Test vi_markets returns US market"""
        markets = provider_us_plugin.vi_markets()
        assert markets == ["US"]
        assert len(markets) == 1

    def test_vi_supported_fields_returns_list(self):
        """Test vi_supported_fields returns list of fields"""
        fields = provider_us_plugin.vi_supported_fields()
        assert isinstance(fields, list)
        assert len(fields) > 0

    def test_vi_supported_fields_contains_financial_fields(self):
        """Test supported fields contain financial fields"""
        fields = provider_us_plugin.vi_supported_fields()
        expected_fields = ["total_assets", "roe", "net_profit", "basic_eps"]
        for field in expected_fields:
            assert field in fields, f"{field} should be in supported fields"

    def test_supported_fields_count(self):
        """Test supported fields count"""
        fields = provider_us_plugin.vi_supported_fields()
        # 美股字段数应该大于 30
        assert len(fields) > 30, f"Expected more than 30 fields, got {len(fields)}"


class TestUSProvider:
    """Test USProvider class"""

    def test_supported_fields_is_set_from_method(self):
        """Test get_supported_fields returns a set"""
        fields = USProvider.get_supported_fields()
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
        supported = USProvider.get_supported_fields()
        for field in balance_fields:
            assert field in supported

    def test_supported_fields_contains_indicator_fields(self):
        """Test get_supported_fields contains indicator fields"""
        indicator_fields = {
            "roe",
            "roa",
            "gross_margin",
            "net_profit_margin",
        }
        supported = USProvider.get_supported_fields()
        for field in indicator_fields:
            assert field in supported

    def test_supported_fields_contains_daily_fields(self):
        """Test get_supported_fields contains daily fields"""
        daily_fields = {
            "open",
            "high",
            "low",
            "close",
            "volume",
        }
        supported = USProvider.get_supported_fields()
        for field in daily_fields:
            assert field in supported

    def test_field_mappings_defined(self):
        """Test FIELD_MAPPINGS is defined"""
        assert hasattr(USProvider, "FIELD_MAPPINGS")
        assert isinstance(USProvider.FIELD_MAPPINGS, dict)

    def test_field_mappings_contains_statement_types(self):
        """Test FIELD_MAPPINGS contains expected statement types"""
        expected_types = ["balance_sheet", "income_statement", "cash_flow", "indicators", "daily"]
        for stmt_type in expected_types:
            assert stmt_type in USProvider.FIELD_MAPPINGS, f"{stmt_type} should be in mappings"

    def test_normalize_symbol_converts_to_uppercase(self):
        """Test _normalize_symbol converts to uppercase"""
        provider = USProvider()
        result = provider._normalize_symbol("aapl")
        assert result == "AAPL"

    def test_normalize_symbol_preserves_existing(self):
        """Test _normalize_symbol preserves existing format"""
        provider = USProvider()
        result = provider._normalize_symbol("GOOGL")
        assert result == "GOOGL"

    def test_get_date_column_returns_report_date(self):
        """Test _get_date_column returns REPORT_DATE"""
        provider = USProvider()
        assert provider._get_date_column() == "REPORT_DATE"


class TestUSProviderFetchMethods:
    """Test USProvider fetch methods"""

    def test_fetch_financials_returns_none_for_empty_fields(self):
        """Test fetch_financials returns None for empty fields"""
        provider = USProvider()

        # Should return None for empty fields
        result = provider.fetch_financials(
            symbol="AAPL",
            fields=set(),
            end_year=2024,
            years=5
        )
        assert result is None

    def test_fetch_indicators_returns_none_for_empty_fields(self):
        """Test fetch_indicators returns None for empty fields"""
        provider = USProvider()

        result = provider.fetch_indicators(
            symbol="AAPL",
            fields=set(),
            end_year=2024,
            years=5
        )
        assert result is None

    def test_fetch_market_returns_none(self):
        """Test fetch_market returns None (US market data not supported)"""
        provider = USProvider()

        result = provider.fetch_market(
            symbol="AAPL",
            fields=set()
        )
        assert result is None


class TestUSProviderIntegration:
    """Integration tests for USProvider (requires API)"""

    @pytest.fixture
    def provider(self):
        """Create provider instance"""
        return USProvider()

    def test_provider_creation(self, provider):
        """Test provider can be created"""
        assert provider is not None
