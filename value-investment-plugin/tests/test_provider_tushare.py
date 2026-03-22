"""Tests for provider_tushare plugin"""
from __future__ import annotations

import pytest
from unittest.mock import patch

from provider_tushare import plugin as tushare_plugin
from provider_tushare.provider import TushareProvider


class TestTushareProviderPlugin:
    """Test TushareProviderPlugin"""

    def test_vi_markets_returns_a(self):
        """Test vi_markets returns A-share market"""
        markets = tushare_plugin.vi_markets()
        assert markets == ["A"]
        assert len(markets) == 1

    def test_vi_supported_fields_returns_list(self):
        """Test vi_supported_fields returns list of fields"""
        fields = tushare_plugin.vi_supported_fields()
        assert isinstance(fields, list)
        assert len(fields) > 0

    def test_vi_supported_fields_contains_financial_fields(self):
        """Test supported fields contain financial fields"""
        fields = tushare_plugin.vi_supported_fields()
        expected_fields = ["total_assets", "roe", "pe_ratio", "close"]
        for field in expected_fields:
            assert field in fields, f"{field} should be in supported fields"

    def test_supported_fields_count(self):
        """Test supported fields count"""
        fields = tushare_plugin.vi_supported_fields()
        # 84 = FIELD_MAPPINGS 所有值（系统标准字段名）
        assert len(fields) == 84, f"Expected 84 fields, got {len(fields)}"


class TestTushareProvider:
    """Test TushareProvider class"""

    def test_supported_fields_is_set_from_method(self):
        """Test get_supported_fields returns a set"""
        fields = TushareProvider.get_supported_fields()
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
        supported = TushareProvider.get_supported_fields()
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
        supported = TushareProvider.get_supported_fields()
        for field in indicator_fields:
            assert field in supported

    def test_supported_fields_contains_market_fields(self):
        """Test get_supported_fields contains market fields"""
        market_fields = {
            "market_cap",
            "pe_ratio",
            "pb_ratio",
            "close",
        }
        supported = TushareProvider.get_supported_fields()
        for field in market_fields:
            assert field in supported

    def test_field_mappings_defined(self):
        """Test FIELD_MAPPINGS is defined"""
        assert hasattr(TushareProvider, "FIELD_MAPPINGS")
        assert isinstance(TushareProvider.FIELD_MAPPINGS, dict)

    def test_field_mappings_contains_statement_types(self):
        """Test FIELD_MAPPINGS contains expected statement types"""
        expected_types = ["balance_sheet", "income_statement", "cash_flow", "indicators", "market"]
        for stmt_type in expected_types:
            assert stmt_type in TushareProvider.FIELD_MAPPINGS, f"{stmt_type} should be in mappings"

    def test_to_ts_code_converts_sz(self):
        """Test _to_ts_code converts SZ stock code"""
        provider = TushareProvider.__new__(TushareProvider)
        provider._token = ""
        provider._api = None

        result = provider._to_ts_code("000001")
        assert result == "000001.SZ"

    def test_to_ts_code_converts_sh(self):
        """Test _to_ts_code converts SH stock code"""
        provider = TushareProvider.__new__(TushareProvider)
        provider._token = ""
        provider._api = None

        result = provider._to_ts_code("600519")
        assert result == "600519.SH"

    def test_to_ts_code_preserves_existing(self):
        """Test _to_ts_code preserves existing ts_code format"""
        provider = TushareProvider.__new__(TushareProvider)
        provider._token = ""
        provider._api = None

        result = provider._to_ts_code("600519.SH")
        assert result == "600519.SH"


class TestTushareProviderFetchMethods:
    """Test TushareProvider fetch methods with mocks"""

    @patch("provider_tushare.provider._get_tushare")
    def test_fetch_financials_returns_dict(self, mock_get_tushare):
        """Test fetch_financials returns expected dict structure"""
        # Create provider without API init
        provider = TushareProvider.__new__(TushareProvider)
        provider._token = ""
        provider._api = None
        provider.FIELD_MAPPINGS = TushareProvider.FIELD_MAPPINGS
        provider._INDICATOR_FIELDS = TushareProvider._INDICATOR_FIELDS
        provider._MARKET_FIELDS = TushareProvider._MARKET_FIELDS
        provider._TRADING_FIELDS = TushareProvider._TRADING_FIELDS

        # Should return None for empty fields
        result = provider.fetch_financials(
            symbol="600519",
            fields=set(),
            end_year=2024,
            years=5
        )
        assert result is None

    @patch("provider_tushare.provider._get_tushare")
    def test_fetch_indicators_returns_none_for_empty_fields(self, mock_get_tushare):
        """Test fetch_indicators returns None for empty fields"""
        provider = TushareProvider.__new__(TushareProvider)
        provider._token = ""
        provider._api = None
        provider.FIELD_MAPPINGS = TushareProvider.FIELD_MAPPINGS
        provider._INDICATOR_FIELDS = TushareProvider._INDICATOR_FIELDS
        provider._MARKET_FIELDS = TushareProvider._MARKET_FIELDS
        provider._TRADING_FIELDS = TushareProvider._TRADING_FIELDS

        result = provider.fetch_indicators(
            symbol="600519",
            fields=set(),
            end_year=2024,
            years=5
        )
        assert result is None

    @patch("provider_tushare.provider._get_tushare")
    def test_fetch_market_returns_empty_for_empty_fields(self, mock_get_tushare):
        """Test fetch_market returns empty dict for empty fields"""
        provider = TushareProvider.__new__(TushareProvider)
        provider._token = ""
        provider._api = None
        provider.FIELD_MAPPINGS = TushareProvider.FIELD_MAPPINGS
        provider._INDICATOR_FIELDS = TushareProvider._INDICATOR_FIELDS
        provider._MARKET_FIELDS = TushareProvider._MARKET_FIELDS
        provider._TRADING_FIELDS = TushareProvider._TRADING_FIELDS

        result = provider.fetch_market(
            symbol="600519",
            fields=set()
        )
        assert result == {}


class TestTushareProviderIntegration:
    """Integration tests for TushareProvider (requires API)"""

    @pytest.fixture
    def provider(self):
        """Create provider instance"""
        return TushareProvider()

    def test_provider_creation(self, provider):
        """Test provider can be created"""
        assert provider is not None
