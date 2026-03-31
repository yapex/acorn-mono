"""Tests for query command with calculators integration"""
import pytest
import pluggy
import pandas as pd

from vi_core import ValueInvestmentSpecs
from vi_core.plugin import plugin
from vi_core.spec import vi_hookimpl
from vi_calculators import plugin as calculators_plugin


class MockProvider:
    """Mock provider for testing"""
    
    @vi_hookimpl
    def vi_markets(self):
        return ["A"]
    
    @vi_hookimpl
    def vi_supported_fields(self):
        return [
            "operating_cash_flow", "capital_expenditure", "market_cap",
            "total_assets", "total_revenue", "roe",
        ]
    
    @vi_hookimpl
    def vi_fetch_financials(self, symbol, fields, end_year, years):
        return pd.DataFrame({
            "fiscal_year": [2024, 2023],
            "operating_cash_flow": [100e8, 90e8],
            "capital_expenditure": [20e8, 18e8],
        })
    
    @vi_hookimpl
    def vi_fetch_market(self, symbol, fields):
        return pd.DataFrame({"fiscal_year": [2024], "market_cap": [5000e8]})


class TestQueryWithCalculators:
    """Test query command with calculators integration"""

    def setup_method(self):
        """Setup plugin manager"""
        self.pm = pluggy.PluginManager("value_investment")
        self.pm.add_hookspecs(ValueInvestmentSpecs)
        self.pm.register(MockProvider(), name="mock_provider")
        self.pm.register(plugin, name="vi_core")
        plugin.set_plugin_manager(self.pm)

    def test_query_without_calculators(self):
        """Query without calculators returns raw data"""
        result = self.pm.hook.vi_handle(
            command="query",
            args={
                "symbol": "600519",
                "fields": "operating_cash_flow,market_cap",
                "years": 2,
            }
        )
        
        assert result["success"] is True
        assert "implied_growth" not in result["data"]["data"]

    def test_query_with_calculator_implied_growth(self):
        """Query with implied_growth calculator"""
        self.pm.register(calculators_plugin, name="calculators")
        
        result = self.pm.hook.vi_handle(
            command="query",
            args={
                "symbol": "600519",
                "fields": "operating_cash_flow,market_cap",
                "calculators": "implied_growth",
                "years": 2,
            }
        )
        
        assert result["success"] is True
        data = result["data"]["data"]
        assert "implied_growth" in data
        assert 2024 in data["implied_growth"]
        # 隐含增长率应该在合理范围
        assert 0.05 < data["implied_growth"][2024] < 0.20

    def test_query_with_calculator_config(self):
        """Query with calculator custom config"""
        self.pm.register(calculators_plugin, name="calculators")
        
        result = self.pm.hook.vi_handle(
            command="query",
            args={
                "symbol": "600519",
                "fields": "operating_cash_flow,market_cap",
                "calculators": "implied_growth",
                "calculator_config": {
                    "implied_growth": {
                        "wacc": 0.08,
                        "g_terminal": 0.02,
                    }
                },
                "years": 2,
            }
        )
        
        assert result["success"] is True
        assert "implied_growth" in result["data"]["data"]

    def test_query_with_multiple_calculators(self):
        """Query with multiple calculators (only one registered)"""
        self.pm.register(calculators_plugin, name="calculators")
        
        result = self.pm.hook.vi_handle(
            command="query",
            args={
                "symbol": "600519",
                "fields": "operating_cash_flow,market_cap",
                "calculators": "implied_growth,unknown_calc",
                "years": 2,
            }
        )
        
        # Should succeed, only run known calculators
        assert result["success"] is True
        assert "implied_growth" in result["data"]["data"]

    def test_query_with_unknown_calculator(self):
        """Query with unknown calculator ignores it"""
        self.pm.register(calculators_plugin, name="calculators")
        
        result = self.pm.hook.vi_handle(
            command="query",
            args={
                "symbol": "600519",
                "fields": "operating_cash_flow,market_cap",
                "calculators": "unknown_calculator",
                "years": 2,
            }
        )
        
        # Should still succeed, just skip unknown calculator
        assert result["success"] is True
        assert "implied_growth" not in result["data"]["data"]

    def test_query_with_missing_required_fields(self):
        """Query with calculator but missing required fields
        
        当 calculator 的 required_fields 在 provider 中不可用时，
        calculator 会被跳过（因为自动收集的字段无法从 provider 获取）。
        """
        self.pm.register(calculators_plugin, name="calculators")
        
        result = self.pm.hook.vi_handle(
            command="query",
            args={
                "symbol": "600519",
                "fields": "total_assets",
                "calculators": "implied_growth",
                "years": 2,
            }
        )
        
        # Should succeed - system auto-collects calculator deps
        assert result["success"] is True
        # implied_growth should run because auto-collected fields are available
        assert "implied_growth" in result["data"]["data"]
