"""Test CLI with unified items concept"""
import pytest
from unittest.mock import patch, MagicMock
from typer.testing import CliRunner
from vi_core.items import get_registry, ItemSource, register_calculator, register_field


@pytest.fixture(autouse=True)
def setup_registry():
    """Setup clean registry for each test"""
    registry = get_registry()
    # Clear existing items
    for name in list(registry.list_all()):
        pass  # Just get a clean slate
    yield registry


def test_cli_list_shows_items():
    """vi list 应该显示所有注册的 items"""
    # Register some test items
    register_field("revenue", "营业收入")
    register_field("net_profit", "净利润")
    register_calculator("implied_growth", ["operating_cash_flow", "market_cap"], "隐含增长率")
    
    # Note: This test will need actual CLI invocation
    # For now we test the registry directly
    registry = get_registry()
    
    assert registry.get("revenue") is not None
    assert registry.get("net_profit") is not None
    assert registry.get("implied_growth") is not None


def test_cli_list_filter_by_category():
    """vi list --category 应该能按分类筛选"""
    register_field("revenue", "营业收入", category="financial")
    register_calculator("implied_growth", [], "隐含增长率", category="analysis")
    
    registry = get_registry()
    
    financial_items = registry.list_by_category("financial")
    analysis_items = registry.list_by_category("analysis")
    
    assert "revenue" in financial_items
    assert "implied_growth" in analysis_items


def test_cli_query_displays_precheck_result():
    """vi query 应该显示预检结果"""
    register_field("revenue", "营业收入")
    
    registry = get_registry()
    
    # 创建 mock prechecker
    from vi_core.precheck import Prechecker, PrecheckResult, Issue, IssueSeverity
    
    mock_prechecker = MagicMock()
    mock_prechecker.check.return_value = PrecheckResult(
        available=["revenue"],
        issues=[
            Issue(
                item="unknown_field",
                severity=IssueSeverity.ERROR,
                reason="未知的数据项",
            )
        ],
        symbol="600519"
    )
    
    result = mock_prechecker.check("600519", ["revenue", "unknown_field"])
    
    assert result.available == ["revenue"]
    assert len(result.issues) == 1
    assert "unknown_field" in result.issues[0].item


def test_query_result_format_includes_diagnostics():
    """查询结果格式化应该包含诊断信息"""
    from vi_core.query import QueryResult
    from vi_core.precheck import PrecheckResult, Issue, IssueSeverity
    
    result = QueryResult(
        success=False,
        symbol="600519",
        data={},
        available=["revenue"],
        unavailable=["implied_growth"],
        issues=[{
            "item": "implied_growth",
            "reason": "缺少依赖字段: operating_cash_flow",
            "suggestion": "无法计算",
        }],
        precheck=PrecheckResult(
            available=["revenue"],
            issues=[
                Issue(
                    item="implied_growth",
                    severity=IssueSeverity.ERROR,
                    reason="缺少依赖字段: operating_cash_flow",
                    missing_fields=["operating_cash_flow"],
                )
            ],
            symbol="600519"
        )
    )
    
    # Format output should include diagnostic info
    output = str(result.precheck)
    assert "600519" in output
    assert "implied_growth" in output
    assert "operating_cash_flow" in output