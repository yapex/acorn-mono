"""Integration tests for CLI core logic"""
import pytest
from unittest.mock import patch, MagicMock
from vi_core.query import QueryEngine
from vi_core.precheck import Prechecker, PrecheckResult, Issue, IssueSeverity
from vi_core.items import ItemRegistry, ItemSource, register_field, register_calculator


@pytest.fixture(autouse=True)
def clean_registry():
    """Clean registry before each test"""
    # Clear the global registry by replacing it
    import vi_core.items as items_module
    items_module._global_registry = ItemRegistry()
    yield
    items_module._global_registry = None


def test_query_engine_with_real_prechecker():
    """QueryEngine 应该与真实 Prechecker 集成"""
    registry = ItemRegistry()
    registry.register_field(name="revenue", description="营业收入")
    registry.register_field(name="net_profit", description="净利润")
    
    prechecker = Prechecker(
        provider_fields={"revenue", "net_profit"},
        registry=registry
    )
    
    engine = QueryEngine(prechecker=prechecker, registry=registry)
    
    with patch.object(engine, '_fetch_data', return_value={"revenue": {2023: 1000}}):
        result = engine.query("600519", ["revenue", "net_profit"])
    
    assert result.success is True
    assert set(result.available) == {"revenue", "net_profit"}
    assert result.precheck is not None
    assert result.precheck.success is True


def test_query_engine_precheck_failure_shows_diagnostics():
    """预检失败时应该返回诊断信息
    
    注意：当有部分 items 可用时，query 仍返回 success=True，
    但会在 unavailable 和 issues 中包含不可用 items 的诊断信息。
    """
    registry = ItemRegistry()
    registry.register_field(name="revenue", description="营业收入")
    registry.register_calculator(
        name="implied_growth",
        requires=["operating_cash_flow", "market_cap"],
        description="隐含增长率"
    )
    
    prechecker = Prechecker(
        provider_fields={"revenue"},  # implied_growth 的依赖不满足
        registry=registry
    )
    
    engine = QueryEngine(prechecker=prechecker, registry=registry)
    
    with patch.object(engine, '_fetch_data', return_value={"revenue": {2023: 1000}}):
        result = engine.query("600519", ["revenue", "implied_growth"])
    
    # 有部分成功，所以 success=True
    assert result.success is True
    assert "revenue" in result.available
    assert "implied_growth" in result.unavailable
    assert len(result.issues) > 0
    
    # 验证诊断信息包含缺失的依赖
    implied_growth_issue = next(i for i in result.issues if i["item"] == "implied_growth")
    assert "operating_cash_flow" in implied_growth_issue["reason"]
    assert "market_cap" in implied_growth_issue["reason"]
    
    # 验证预检结果中 has_errors 为 True
    assert result.precheck.has_errors is True


def test_precheck_result_format_shows_issues():
    """预检结果格式化应该显示问题"""
    result = PrecheckResult(
        available=["revenue"],
        issues=[
            Issue(
                item="implied_growth",
                severity=IssueSeverity.ERROR,
                reason="缺少依赖字段: operating_cash_flow, market_cap",
                missing_fields=["operating_cash_flow", "market_cap"],
                suggestion="无法计算 implied_growth"
            )
        ],
        symbol="600519"
    )
    
    formatted = str(result)
    
    assert "600519" in formatted
    assert "revenue" in formatted
    assert "implied_growth" in formatted
    assert "operating_cash_flow" in formatted
    assert "market_cap" in formatted


def test_calculator_priority_over_field():
    """Calculator 应该优先于 Field（同名称时）"""
    # 注册同名的 Field 和 Calculator
    register_field(name="roe", description="ROE from field")
    register_calculator(
        name="roe",
        requires=["net_profit", "equity"],
        description="ROE calculated"
    )
    
    registry = ItemRegistry()
    registry.register_field(name="roe", description="ROE from field")
    registry.register_calculator(
        name="roe",
        requires=["net_profit", "equity"],
        description="ROE calculated"
    )
    
    item = registry.get("roe")
    assert item.source == ItemSource.CALCULATOR


def test_item_registry_integration_with_precheck():
    """ItemRegistry 和 Prechecker 应该正确集成"""
    registry = ItemRegistry()
    
    # 注册 items
    registry.register_field(name="revenue", description="营业收入", category="financial")
    registry.register_field(name="net_profit", description="净利润", category="financial")
    registry.register_field(name="operating_cash_flow", description="经营活动现金流", category="financial")
    registry.register_field(name="market_cap", description="市值", category="market")
    registry.register_calculator(
        name="implied_growth",
        requires=["operating_cash_flow", "market_cap"],
        description="隐含增长率",
        category="analysis"
    )
    
    prechecker = Prechecker(
        provider_fields={"revenue", "net_profit", "operating_cash_flow", "market_cap"},
        registry=registry
    )
    
    result = prechecker.check("600519", ["revenue", "implied_growth"])
    
    assert result.success is True
    assert set(result.available) == {"revenue", "implied_growth"}
    
    # 按分类查询
    financial_items = registry.list_by_category("financial")
    analysis_items = registry.list_by_category("analysis")
    
    assert "revenue" in financial_items
    assert "net_profit" in financial_items
    assert "implied_growth" in analysis_items