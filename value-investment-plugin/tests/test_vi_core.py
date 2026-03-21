"""Tests for vi_core plugin"""
from __future__ import annotations

import pytest

from vi_core import plugin as vi_core_plugin
from vi_core import ValueInvestmentSpecs


class TestViCorePlugin:
    """Test ViCorePlugin"""

    def setup_method(self):
        """Setup plugin manager for each test"""
        import pluggy

        self.pm = pluggy.PluginManager("value_investment")
        self.pm.add_hookspecs(ValueInvestmentSpecs)
        self.pm.register(vi_core_plugin, name="vi_core")
        vi_core_plugin.set_plugin_manager(self.pm)

    def test_vi_commands(self):
        """Test vi_commands returns expected commands"""
        commands = vi_core_plugin.vi_commands()
        assert "list_fields" in commands
        assert "query" in commands

    def test_vi_fields_returns_core_fields(self):
        """Test vi_fields returns core fields structure"""
        result = vi_core_plugin.vi_fields()
        assert result["source"] == "core"
        assert result["fields"] == set()
        assert "description" in result

    def test_list_fields_command(self):
        """Test list_fields command works"""
        result = vi_core_plugin._list_fields({})
        assert result["success"] is True
        assert "fields" in result["data"]
        assert "by_source" in result["data"]

    def test_list_fields_with_source_filter(self):
        """Test list_fields with source filter"""
        result = vi_core_plugin._list_fields({"source": "ifrs"})
        assert result["success"] is True
        # Should only return ifrs fields

    def test_query_missing_symbol(self):
        """Test query fails without symbol"""
        result = vi_core_plugin._query({})
        assert result["success"] is False
        assert "symbol" in result["error"]

    def test_query_empty_fields(self):
        """Test query fails with empty fields"""
        result = vi_core_plugin._query({"symbol": "600519", "fields": ""})
        assert result["success"] is False
        assert "No valid fields" in result["error"]

    def test_query_unknown_command(self):
        """Test unknown command returns error"""
        result = vi_core_plugin.vi_handle("unknown_cmd", {})
        assert result["success"] is False
        assert "Unknown command" in result["error"]


class TestValueInvestmentSpecs:
    """Test hook specifications"""

    def test_specs_combined(self):
        """Test ValueInvestmentSpecs combines all specs"""
        assert hasattr(ValueInvestmentSpecs, "vi_fields")
        assert hasattr(ValueInvestmentSpecs, "vi_markets")
        assert hasattr(ValueInvestmentSpecs, "vi_supported_fields")
        assert hasattr(ValueInvestmentSpecs, "vi_fetch_financials")
        assert hasattr(ValueInvestmentSpecs, "vi_fetch_indicators")
        assert hasattr(ValueInvestmentSpecs, "vi_fetch_market")
        assert hasattr(ValueInvestmentSpecs, "vi_list_calculators")
        assert hasattr(ValueInvestmentSpecs, "vi_commands")
        assert hasattr(ValueInvestmentSpecs, "vi_handle")
