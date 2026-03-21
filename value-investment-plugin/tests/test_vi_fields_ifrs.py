"""Tests for vi_fields_ifrs plugin"""
from __future__ import annotations


from vi_fields_ifrs import plugin as ifrs_plugin
from vi_fields_ifrs.plugin import IFRS_FIELDS


class TestViFieldsIfrsPlugin:
    """Test ViFieldsIfrsPlugin"""

    def test_vi_fields_returns_ifrs_fields(self):
        """Test vi_fields returns IFRS standard fields"""
        result = ifrs_plugin.vi_fields()
        assert result["source"] == "ifrs"
        assert "fields" in result
        assert len(result["fields"]) > 0
        assert "description" in result

    def test_ifrs_fields_contains_balance_sheet(self):
        """Test IFRS fields contain balance sheet fields"""
        balance_sheet_fields = {
            "total_assets",
            "total_liabilities",
            "total_equity",
            "current_assets",
            "current_liabilities",
        }
        for field in balance_sheet_fields:
            assert field in IFRS_FIELDS, f"{field} should be in IFRS_FIELDS"

    def test_ifrs_fields_contains_income_statement(self):
        """Test IFRS fields contain income statement fields"""
        income_fields = {
            "total_revenue",
            "net_profit",
            "operating_profit",
        }
        for field in income_fields:
            assert field in IFRS_FIELDS, f"{field} should be in IFRS_FIELDS"

    def test_ifrs_fields_contains_ratios(self):
        """Test IFRS fields contain ratio fields"""
        ratio_fields = {
            "roe",
            "roa",
            "gross_margin",
            "pe_ratio",
            "pb_ratio",
        }
        for field in ratio_fields:
            assert field in IFRS_FIELDS, f"{field} should be in IFRS_FIELDS"

    def test_ifrs_fields_is_set(self):
        """Test IFRS_FIELDS is a set"""
        assert isinstance(IFRS_FIELDS, set)

    def test_ifrs_fields_count(self):
        """Test IFRS fields count matches expected"""
        assert len(IFRS_FIELDS) == 38, f"Expected 38 fields, got {len(IFRS_FIELDS)}"
