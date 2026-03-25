"""Tests for vi_provide_items hook"""
import sys
from pathlib import Path

import pandas as pd

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from vi_core.query import QueryEngine


class MockProvider:
    """Mock Provider for testing"""
    
    def __init__(self, market_code: str, supported_fields: set[str]):
        self.market_code = market_code
        self.supported_fields = supported_fields
    
    def vi_provide_items(self, items, symbol, market, end_year, years):
        """Mock implementation"""
        if market != self.market_code:
            return None
        
        available = set(items) & self.supported_fields
        if not available:
            return None
        
        # 返回模拟数据
        data = {field: [100, 200, 300] for field in available}
        data["fiscal_year"] = [2021, 2022, 2023]
        return pd.DataFrame(data)


class TestViProvideItems:
    """Test vi_provide_items hook"""
    
    def test_market_filtering(self):
        """测试市场过滤 - Provider 只响应自己的市场"""
        # 创建模拟 Provider
        hk_provider = MockProvider("HK", {"net_profit", "roe"})
        us_provider = MockProvider("US", {"net_profit", "roa"})
        
        # HK Provider 应该忽略 US 市场的请求
        result = hk_provider.vi_provide_items(
            items=["net_profit", "roe"],
            symbol="AAPL",
            market="US",
            end_year=2023,
            years=3,
        )
        assert result is None
        
        # US Provider 应该响应 US 市场的请求
        result = us_provider.vi_provide_items(
            items=["net_profit", "roa"],
            symbol="AAPL",
            market="US",
            end_year=2023,
            years=3,
        )
        assert result is not None
        assert "net_profit" in result.columns
    
    def test_field_filtering(self):
        """测试字段过滤 - Provider 只返回支持的字段"""
        provider = MockProvider("HK", {"net_profit", "roe"})
        
        result = provider.vi_provide_items(
            items=["net_profit", "roe", "unsupported_field"],
            symbol="00700",
            market="HK",
            end_year=2023,
            years=3,
        )
        
        assert result is not None
        assert "net_profit" in result.columns
        assert "roe" in result.columns
        assert "unsupported_field" not in result.columns
    
    def test_empty_items_returns_none(self):
        """测试空字段列表返回 None"""
        provider = MockProvider("HK", {"net_profit"})
        
        result = provider.vi_provide_items(
            items=["unsupported_field"],
            symbol="00700",
            market="HK",
            end_year=2023,
            years=3,
        )
        
        assert result is None


class TestQueryEngineMarketInference:
    """Test QueryEngine market inference"""
    
    def test_infer_a_market(self):
        """测试推断 A 股市场"""
        engine = QueryEngine()
        assert engine._infer_market("600519") == "A"
        assert engine._infer_market("000001") == "A"
    
    def test_infer_hk_market(self):
        """测试推断港股市场"""
        engine = QueryEngine()
        assert engine._infer_market("00700") == "HK"
        assert engine._infer_market("09988") == "HK"
    
    def test_infer_us_market(self):
        """测试推断美股市场"""
        engine = QueryEngine()
        assert engine._infer_market("AAPL") == "US"
        assert engine._infer_market("GOOGL") == "US"
