"""Tests for provider_market_a plugin"""
from __future__ import annotations

import pytest
from unittest.mock import patch

from provider_market_a.plugin import plugin as provider_a_plugin
from provider_market_a.provider import TushareProvider


class TestProviderAMarketPlugin:
    """Test ProviderAPlugin"""

    def test_vi_markets_returns_a(self):
        """Test vi_markets returns A-share market"""
        markets = provider_a_plugin.vi_markets()
        assert markets == ["A"]
        assert len(markets) == 1

    def test_vi_supported_fields_returns_list(self):
        """Test vi_supported_fields returns list of fields"""
        fields = provider_a_plugin.vi_supported_fields()
        assert isinstance(fields, list)
        assert len(fields) > 0

    def test_vi_supported_fields_contains_financial_fields(self):
        """Test supported fields contain financial fields"""
        fields = provider_a_plugin.vi_supported_fields()
        expected_fields = ["total_assets", "roe", "pe_ratio", "close"]
        for field in expected_fields:
            assert field in fields, f"{field} should be in supported fields"

    def test_supported_fields_count(self):
        """Test supported fields count"""
        fields = provider_a_plugin.vi_supported_fields()
        # 85 = FIELD_MAPPINGS 所有值（系统标准字段名）
        assert len(fields) == 85, f"Expected 85 fields, got {len(fields)}"


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

    def test_normalize_symbol_converts_sz(self):
        """Test _normalize_symbol converts SZ stock code"""
        provider = TushareProvider()
        result = provider._normalize_symbol("000001")
        assert result == "000001.SZ"

    def test_normalize_symbol_converts_sh(self):
        """Test _normalize_symbol converts SH stock code"""
        provider = TushareProvider()
        result = provider._normalize_symbol("600519")
        assert result == "600519.SH"

    def test_normalize_symbol_preserves_existing(self):
        """Test _normalize_symbol preserves existing ts_code format"""
        provider = TushareProvider()
        result = provider._normalize_symbol("600519.SH")
        assert result == "600519.SH"


class TestTushareProviderFetchMethods:
    """Test TushareProvider fetch methods"""

    def test_fetch_financials_returns_none_for_empty_fields(self):
        """Test fetch_financials returns None for empty fields"""
        provider = TushareProvider()

        # Should return None for empty fields
        result = provider.fetch_financials(
            symbol="600519",
            fields=set(),
            end_year=2024,
            years=5
        )
        assert result is None

    def test_fetch_indicators_returns_none_for_empty_fields(self):
        """Test fetch_indicators returns None for empty fields"""
        provider = TushareProvider()

        result = provider.fetch_indicators(
            symbol="600519",
            fields=set(),
            end_year=2024,
            years=5
        )
        assert result is None

    def test_fetch_market_returns_none_for_empty_fields(self):
        """Test fetch_market returns None for empty fields"""
        provider = TushareProvider()

        result = provider.fetch_market(
            symbol="600519",
            fields=set()
        )
        assert result is None


class TestTushareProviderIntegration:
    """Integration tests for TushareProvider (requires API)"""

    @pytest.fixture
    def provider(self):
        """Create provider instance"""
        return TushareProvider()

    def test_provider_creation(self, provider):
        """Test provider can be created"""
        assert provider is not None
