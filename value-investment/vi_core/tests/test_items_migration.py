"""Test Items Migration - Calculator 到 ItemRegistry 的迁移"""
import pytest
from unittest.mock import MagicMock, patch


def test_calculator_syncs_to_item_registry():
    """CalculatorEngine 加载的计算器应该同步到 ItemRegistry"""
    from vi_core.items import ItemRegistry, ItemSource, get_registry
    from vi_core.plugin import ViCorePlugin
    
    # Mock plugin manager
    mock_pm = MagicMock()
    mock_pm.hook.vi_list_calculators.return_value = [
        {
            "name": "implied_growth",
            "required_fields": ["operating_cash_flow", "market_cap"],
            "description": "隐含增长率",
            "namespace": "builtin",
        }
    ]
    mock_pm.hook.vi_fields.return_value = []
    mock_pm.hook.vi_supported_fields.return_value = []
    ViCorePlugin._pm = mock_pm
    
    # 清除全局注册表
    import vi_core.items as items_module
    items_module._global_registry = ItemRegistry()
    
    registry = get_registry()
    
    # 验证同步前没有 implied_growth
    assert registry.get("implied_growth") is None
    
    # 调用同步方法
    ViCorePlugin.sync_items_to_registry()
    
    # 验证同步后有了
    item = registry.get("implied_growth")
    assert item is not None
    assert item.source == ItemSource.CALCULATOR
    assert "operating_cash_flow" in item.requires
    assert "market_cap" in item.requires
    assert item.description == "隐含增长率"
    
    ViCorePlugin._pm = None


def test_field_syncs_to_item_registry():
    """vi_fields hook 返回的字段应该同步到 ItemRegistry"""
    from vi_core.items import ItemRegistry, ItemSource, get_registry
    from vi_core.plugin import ViCorePlugin
    
    # Mock plugin manager
    mock_pm = MagicMock()
    mock_pm.hook.vi_list_calculators.return_value = []
    mock_pm.hook.vi_fields.return_value = [
        {
            "source": "ifrs",
            "fields": {
                "revenue": {"description": "营业收入"},
                "net_profit": {"description": "净利润"},
            }
        }
    ]
    mock_pm.hook.vi_supported_fields.return_value = []
    ViCorePlugin._pm = mock_pm
    
    # 清除全局注册表
    import vi_core.items as items_module
    items_module._global_registry = ItemRegistry()
    
    registry = get_registry()
    
    # 调用同步方法
    ViCorePlugin.sync_items_to_registry()
    
    # 验证字段已同步
    revenue_item = registry.get("revenue")
    assert revenue_item is not None
    assert revenue_item.source == ItemSource.FIELD
    assert revenue_item.description == "营业收入"
    
    ViCorePlugin._pm = None


def test_calculator_takes_priority_over_field():
    """同名的 Calculator 应该优先于 Field"""
    from vi_core.items import ItemRegistry, ItemSource, get_registry
    from vi_core.plugin import ViCorePlugin
    
    # Mock plugin manager - both have "roe"
    mock_pm = MagicMock()
    mock_pm.hook.vi_list_calculators.return_value = [
        {
            "name": "roe",
            "required_fields": ["net_profit", "equity"],
            "description": "ROE calculated",
            "namespace": "builtin",
        }
    ]
    mock_pm.hook.vi_fields.return_value = [
        {
            "source": "ifrs",
            "fields": {
                "roe": {"description": "ROE from field"},
            }
        }
    ]
    mock_pm.hook.vi_supported_fields.return_value = ["roe"]
    ViCorePlugin._pm = mock_pm
    
    # 清除全局注册表
    import vi_core.items as items_module
    items_module._global_registry = ItemRegistry()
    
    registry = get_registry()
    
    # 调用同步方法
    ViCorePlugin.sync_items_to_registry()
    
    # Calculator 应该优先
    item = registry.get("roe")
    assert item is not None
    assert item.source == ItemSource.CALCULATOR
    assert item.description == "ROE calculated"
    
    ViCorePlugin._pm = None


def test_sync_items_from_multiple_sources():
    """应该能同步来自多个来源的 items"""
    from vi_core.items import ItemRegistry, ItemSource, get_registry
    from vi_core.plugin import ViCorePlugin
    
    mock_pm = MagicMock()
    mock_pm.hook.vi_list_calculators.return_value = [
        {"name": "calc1", "required_fields": [], "description": "Calc 1", "namespace": "builtin"}
    ]
    mock_pm.hook.vi_fields.return_value = [
        {"source": "provider_a", "fields": {"field_a": {"description": "Field A"}}},
        {"source": "provider_b", "fields": {"field_b": {"description": "Field B"}}},
    ]
    mock_pm.hook.vi_supported_fields.return_value = ["field_a", "field_b"]
    ViCorePlugin._pm = mock_pm
    
    import vi_core.items as items_module
    items_module._global_registry = ItemRegistry()
    registry = get_registry()
    
    ViCorePlugin.sync_items_to_registry()
    
    assert registry.get("calc1") is not None
    assert registry.get("field_a") is not None
    assert registry.get("field_b") is not None
    
    ViCorePlugin._pm = None