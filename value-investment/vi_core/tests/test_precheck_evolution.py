"""Test Precheck Evolution Integration - 验证 capability_type 区分"""
import pytest
from unittest.mock import patch, MagicMock
from vi_core.precheck import Prechecker
from vi_core.items import ItemRegistry, ItemSource


def test_precheck_publishes_calculator_event_when_calc_usable():
    """当 Calculator 可用时（依赖满足）不应该发布 Evolution 事件"""
    registry = ItemRegistry()
    registry.register_calculator(
        name="implied_growth",
        requires=["operating_cash_flow"],
        description="隐含增长率"
    )
    # operating_cash_flow 是 Field（从 Provider 获取），不是 Calculator
    registry.register_field(
        name="operating_cash_flow",
        description="经营活动现金流"
    )
    
    prechecker = Prechecker(
        provider_fields={"operating_cash_flow"},  # 依赖满足
        registry=registry
    )
    
    with patch("vi_core.evolution.publish_capability_missing") as mock_publish:
        # implied_growth 存在且依赖满足，应该可用
        result = prechecker.check("600519", ["implied_growth"])
        # 不应该发布事件
        mock_publish.assert_not_called()
        assert result.available == ["implied_growth"]


def test_precheck_publishes_field_event_on_field_missing():
    """Field 缺失时应该发布 field 类型的 Evolution 事件"""
    registry = ItemRegistry()
    registry.register_field(name="revenue", description="营业收入")
    # market_cap 没有注册为 provider_fields
    
    prechecker = Prechecker(
        provider_fields={"revenue"},  # 只支持 revenue
        registry=registry
    )
    
    with patch("vi_core.evolution.publish_capability_missing") as mock_publish:
        prechecker.check("600519", ["market_cap"])
        
        mock_publish.assert_called_once()
        call_kwargs = mock_publish.call_args[1]
        assert call_kwargs["capability_type"].value == "field"
        assert call_kwargs["item"] == "market_cap"


def test_precheck_publishes_calculator_event_on_deps_missing():
    """Calculator 依赖缺失时应该发布 calculator 类型的 Evolution 事件"""
    registry = ItemRegistry()
    registry.register_calculator(
        name="implied_growth",
        requires=["operating_cash_flow", "market_cap"],
        description="隐含增长率"
    )
    
    prechecker = Prechecker(
        provider_fields={"operating_cash_flow"},  # 只有一个依赖
        registry=registry
    )
    
    with patch("vi_core.evolution.publish_capability_missing") as mock_publish:
        prechecker.check("00700", ["implied_growth"])
        
        mock_publish.assert_called_once()
        call_kwargs = mock_publish.call_args[1]
        assert call_kwargs["capability_type"].value == "calculator"
        assert call_kwargs["item"] == "implied_growth"
        assert "operating_cash_flow" in call_kwargs["missing_fields"]
        assert "market_cap" in call_kwargs["missing_fields"]


def test_precheck_no_event_when_all_available():
    """当所有 items 都可用时不应该发布事件"""
    registry = ItemRegistry()
    registry.register_field(name="revenue", description="营业收入")
    
    prechecker = Prechecker(
        provider_fields={"revenue"},
        registry=registry
    )
    
    with patch("vi_core.evolution.publish_capability_missing") as mock_publish:
        prechecker.check("600519", ["revenue"])
        
        mock_publish.assert_not_called()


def test_precheck_distinguishes_calc_vs_field():
    """应该能区分是计算器缺失还是字段缺失"""
    registry = ItemRegistry()
    registry.register_field(name="revenue", description="营业收入")
    registry.register_calculator(
        name="implied_growth",
        requires=["operating_cash_flow"],
        description="隐含增长率"
    )
    
    # operating_cash_flow 不在 provider_fields
    prechecker = Prechecker(
        provider_fields={"revenue"},  # revenue 可用，operating_cash_flow 不可用
        registry=registry
    )
    
    with patch("vi_core.evolution.publish_capability_missing") as mock_publish:
        prechecker.check("600519", ["revenue", "implied_growth"])
        
        # 应该调用一次（implied_growth 依赖缺失）
        assert mock_publish.call_count == 1
        
        call_kwargs = mock_publish.call_args[1]
        # 这是计算器的问题（计算器依赖不满足）
        assert call_kwargs["capability_type"].value == "calculator"
        assert call_kwargs["item"] == "implied_growth"


def test_precheck_unknown_item_triggers_field_event():
    """未知的数据项应该触发 field 类型的事件"""
    registry = ItemRegistry()
    # 没有任何注册
    
    prechecker = Prechecker(
        provider_fields=set(),
        registry=registry
    )
    
    with patch("vi_core.evolution.publish_capability_missing") as mock_publish:
        prechecker.check("600519", ["completely_unknown"])
        
        mock_publish.assert_called_once()
        call_kwargs = mock_publish.call_args[1]
        # 未知类型视为 field 缺失
        assert call_kwargs["capability_type"].value == "field"
        assert call_kwargs["item"] == "completely_unknown"