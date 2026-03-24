"""Test Prechecker - 查询前可用性检查"""
import pytest
from unittest.mock import MagicMock
from vi_core.precheck import Prechecker, PrecheckResult, Issue, IssueSeverity
from vi_core.items import ItemRegistry, ItemSource, register_calculator, register_field


def test_precheck_all_available():
    """所有 items 都可用"""
    registry = ItemRegistry()
    registry.register_field(name="revenue", description="营业收入")
    registry.register_field(name="net_profit", description="净利润")
    
    prechecker = Prechecker(
        provider_fields={"revenue", "net_profit"},
        registry=registry
    )
    
    result = prechecker.check("600519", ["revenue", "net_profit"])
    
    assert result.available == ["revenue", "net_profit"]
    assert result.issues == []


def test_precheck_missing_field():
    """缺少 Field"""
    registry = ItemRegistry()
    registry.register_field(name="revenue", description="营业收入")
    
    prechecker = Prechecker(
        provider_fields={"revenue"},
        registry=registry
    )
    
    result = prechecker.check("600519", ["revenue", "unknown_field"])
    
    assert result.available == ["revenue"]
    assert len(result.issues) == 1
    assert result.issues[0].item == "unknown_field"
    assert "unknown_field" in result.issues[0].reason


def test_precheck_calculator_with_missing_deps():
    """Calculator 依赖缺失"""
    registry = ItemRegistry()
    registry.register_calculator(
        name="implied_growth",
        requires=["operating_cash_flow", "market_cap"],
        description="隐含增长率"
    )
    
    prechecker = Prechecker(
        provider_fields={"revenue"},  # 有 revenue，但没有 operating_cash_flow
        registry=registry
    )
    
    result = prechecker.check("600519", ["implied_growth"])
    
    assert result.available == []
    assert len(result.issues) == 1
    assert result.issues[0].item == "implied_growth"
    assert "operating_cash_flow" in result.issues[0].reason


def test_precheck_calculator_with_all_deps():
    """Calculator 所有依赖都满足"""
    registry = ItemRegistry()
    registry.register_calculator(
        name="implied_growth",
        requires=["operating_cash_flow", "market_cap"],
        description="隐含增长率"
    )
    registry.register_field(name="operating_cash_flow", description="经营活动现金流")
    registry.register_field(name="market_cap", description="市值")
    
    prechecker = Prechecker(
        provider_fields={"operating_cash_flow", "market_cap"},
        registry=registry
    )
    
    result = prechecker.check("600519", ["implied_growth"])
    
    assert result.available == ["implied_growth"]
    assert result.issues == []


def test_precheck_mixed():
    """混合场景"""
    registry = ItemRegistry()
    registry.register_field(name="revenue", description="营业收入")
    registry.register_calculator(
        name="implied_growth",
        requires=["operating_cash_flow", "market_cap"],
        description="隐含增长率"
    )
    registry.register_field(name="operating_cash_flow", description="经营活动现金流")
    registry.register_field(name="market_cap", description="市值")
    
    prechecker = Prechecker(
        provider_fields={"revenue", "operating_cash_flow", "market_cap"},
        registry=registry
    )
    
    result = prechecker.check("600519", ["revenue", "implied_growth", "unknown"])
    
    assert set(result.available) == {"revenue", "implied_growth"}
    assert len(result.issues) == 1
    assert result.issues[0].item == "unknown"


def test_precheck_result_success_property():
    """PrecheckResult.success 属性应该正确反映状态"""
    result_ok = PrecheckResult(
        available=["revenue"],
        issues=[],
        symbol="600519"
    )
    assert result_ok.success is True
    assert result_ok.has_errors is False
    
    result_fail = PrecheckResult(
        available=["revenue"],
        issues=[Issue("unknown", IssueSeverity.ERROR, "未知")],
        symbol="600519"
    )
    assert result_fail.success is False
    assert result_fail.has_errors is True


def test_precheck_calculator_nested_deps():
    """Calculator 嵌套依赖检查
    
    当 Calculator c 依赖 Calculator b，b 依赖 Field a 时：
    - 如果 a 可用，b 可用，c 也可用（递归检查）
    """
    registry = ItemRegistry()
    
    # c 需要 b，b 需要 a
    registry.register_field(name="a", description="Field A")
    registry.register_calculator(name="b", requires=["a"], description="Calc B")
    registry.register_calculator(name="c", requires=["b"], description="Calc C")
    
    prechecker = Prechecker(
        provider_fields={"a"},  # a 满足，b 和 c 都应该可用
        registry=registry
    )
    
    result = prechecker.check("600519", ["c"])
    
    # c 的依赖链完整，所以 c 可用
    assert result.available == ["c"]
    assert result.issues == []


def test_precheck_calculator_nested_deps_broken():
    """Calculator 嵌套依赖检查 - 依赖链断裂
    
    当 Calculator c 依赖 Calculator b，b 依赖 Field a 时：
    - 如果 a 不可用，b 不可用，c 也不可用
    """
    registry = ItemRegistry()
    
    # c 需要 b，b 需要 a
    registry.register_field(name="a", description="Field A")
    registry.register_calculator(name="b", requires=["a"], description="Calc B")
    registry.register_calculator(name="c", requires=["b"], description="Calc C")
    
    prechecker = Prechecker(
        provider_fields=set(),  # a 不可用
        registry=registry
    )
    
    result = prechecker.check("600519", ["c"])
    
    assert result.available == []
    assert len(result.issues) == 1
    assert result.issues[0].item == "c"
    # a 是缺失的根源
    assert "a" in result.issues[0].missing_fields


def test_precheck_unknown_item():
    """未知的数据项"""
    registry = ItemRegistry()
    
    prechecker = Prechecker(
        provider_fields=set(),
        registry=registry
    )
    
    result = prechecker.check("600519", ["completely_unknown"])
    
    assert result.available == []
    assert len(result.issues) == 1
    assert result.issues[0].item == "completely_unknown"
    assert result.issues[0].severity == IssueSeverity.ERROR