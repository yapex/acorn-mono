"""Test Item Registry - 统一的数据项注册机制"""
from vi_core.items import ItemRegistry, ItemSource, Item


def test_item_registry_add_calculator():
    """Calculator item 应该能注册"""
    registry = ItemRegistry()

    registry.register_calculator(
        name="implied_growth",
        requires=["operating_cash_flow", "market_cap"],
        description="隐含增长率"
    )

    item = registry.get("implied_growth")
    assert item is not None
    assert item.source == ItemSource.CALCULATOR
    assert "operating_cash_flow" in item.requires
    assert "market_cap" in item.requires


def test_item_registry_add_field():
    """Field item 应该能注册"""
    registry = ItemRegistry()

    registry.register_field(
        name="revenue",
        description="营业总收入"
    )

    item = registry.get("revenue")
    assert item is not None
    assert item.source == ItemSource.FIELD
    assert item.requires == []


def test_item_registry_calculator_takes_priority():
    """同名的 Calculator 应该优先于 Field"""
    registry = ItemRegistry()

    registry.register_field(name="roe", description="ROE from field")
    registry.register_calculator(name="roe", requires=["net_profit", "equity"], description="ROE calculated")

    item = registry.get("roe")
    assert item.source == ItemSource.CALCULATOR


def test_item_registry_list_all():
    """应该能列出所有 items"""
    registry = ItemRegistry()
    registry.register_calculator("calc1", [], "Calc 1")
    registry.register_field("field1", "Field 1")

    all_items = registry.list_all()
    assert "calc1" in all_items
    assert "field1" in all_items


def test_item_registry_list_by_source():
    """应该能按来源列出 Items"""
    registry = ItemRegistry()
    registry.register_calculator("calc1", [], "Calc 1")
    registry.register_field("field1", "Field 1")
    registry.register_field("field2", "Field 2")

    calcs = registry.list_by_source(ItemSource.CALCULATOR)
    fields = registry.list_by_source(ItemSource.FIELD)

    assert calcs == ["calc1"]
    assert set(fields) == {"field1", "field2"}


def test_item_registry_list_by_category():
    """应该能按分类列出 Items"""
    registry = ItemRegistry()
    registry.register_calculator("calc1", [], "Calc 1", category="analysis")
    registry.register_field("field1", "Field 1", category="financial")

    analysis_items = registry.list_by_category("analysis")
    financial_items = registry.list_by_category("financial")

    assert "calc1" in analysis_items
    assert "field1" in financial_items


def test_global_registry():
    """全局注册表应该可用"""
    from vi_core.items import get_registry, register_calculator, register_field

    # 注册一个 item
    register_calculator("test_global_calc", ["revenue"], "Test calculator")
    register_field("test_global_field", "Test field")

    # 从全局注册表获取
    registry = get_registry()
    assert registry.get("test_global_calc") is not None
    assert registry.get("test_global_field") is not None


def test_item_dataclass():
    """Item 数据类应该正确存储信息"""
    item = Item(
        name="test_item",
        description="Test description",
        source=ItemSource.FIELD,
        requires=[],
        category="financial"
    )

    assert item.name == "test_item"
    assert item.description == "Test description"
    assert item.source == ItemSource.FIELD
    assert item.requires == []
    assert item.category == "financial"
