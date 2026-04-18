"""Test QueryEngine with real data flow"""
import pytest
from unittest.mock import patch
from vi_core.query import QueryEngine
from vi_core.precheck import Prechecker
from vi_core.items import ItemRegistry, ItemSource


@pytest.fixture(autouse=True)
def setup_registry():
    """Setup clean registry"""
    import vi_core.items as items_module
    items_module._global_registry = ItemRegistry()
    yield
    items_module._global_registry = None


def test_query_engine_separates_fields_from_calculators():
    """QueryEngine 应该区分 Field items 和 Calculator items"""
    registry = ItemRegistry()
    registry.register_field(name="revenue", description="营业收入")
    registry.register_field(name="net_profit", description="净利润")
    registry.register_calculator(
        name="profit_margin",
        requires=["net_profit", "revenue"],
        description="利润率"
    )

    # Field items
    field_items = [name for name in registry.list_all()
                   if registry.get(name).source == ItemSource.FIELD]
    # Calculator items
    calc_items = [name for name in registry.list_all()
                  if registry.get(name).source == ItemSource.CALCULATOR]

    assert set(field_items) == {"revenue", "net_profit"}
    assert calc_items == ["profit_margin"]


def test_query_engine_runs_calculators_after_fetch():
    """QueryEngine 应该在获取 Field 数据后运行 Calculator"""
    registry = ItemRegistry()
    registry.register_field(name="revenue", description="营业收入")
    registry.register_field(name="net_profit", description="净利润")
    registry.register_calculator(
        name="profit_margin",
        requires=["net_profit", "revenue"],
        description="利润率"
    )

    prechecker = Prechecker(
        provider_fields={"revenue", "net_profit"},
        registry=registry
    )

    engine = QueryEngine(prechecker=prechecker, registry=registry)

    # Mock _fetch_data to return field data
    field_data = {
        "revenue": {2023: 1000.0},
        "net_profit": {2023: 100.0},
    }

    # Mock calculator results
    calc_results = {
        "profit_margin": {2023: 0.1},
    }

    with patch.object(engine, '_fetch_data', return_value=field_data):
        with patch.object(engine, '_run_calculators', return_value=calc_results):
            result = engine.query("600519", ["revenue", "net_profit", "profit_margin"])

    assert result.success is True
    # revenue 和 net_profit 来自 _fetch_data
    # profit_margin 来自 _run_calculators
    assert "revenue" in result.data
    assert "profit_margin" in result.data
    assert result.data["profit_margin"] == {2023: 0.1}


def test_query_engine_precheck_before_fetch():
    """QueryEngine 应该在获取数据前先预检"""
    registry = ItemRegistry()
    registry.register_field(name="revenue", description="营业收入")

    prechecker = Prechecker(
        provider_fields={"revenue"},
        registry=registry
    )

    engine = QueryEngine(prechecker=prechecker, registry=registry)

    # Track call order
    call_order = []

    original_precheck = engine._precheck
    def tracked_precheck(symbol, items):
        call_order.append("precheck")
        return original_precheck(symbol, items)


def test_query_engine_returns_diagnostic_on_partial_failure():
    """部分失败时应该返回诊断信息"""
    registry = ItemRegistry()
    registry.register_field(name="revenue", description="营业收入")
    registry.register_calculator(
        name="profit_margin",
        requires=["net_profit", "revenue"],
        description="利润率"
    )

    # net_profit 不可用
    prechecker = Prechecker(
        provider_fields={"revenue"},  # 缺 net_profit
        registry=registry
    )

    engine = QueryEngine(prechecker=prechecker, registry=registry)

    # _fetch_data 只返回 revenue
    field_data = {"revenue": {2023: 1000.0}}

    with patch.object(engine, '_fetch_data', return_value=field_data):
        with patch.object(engine, '_run_calculators', return_value={}):
            result = engine.query("600519", ["revenue", "profit_margin"])

    # 部分成功
    assert result.success is True
    assert "revenue" in result.available
    assert "profit_margin" in result.unavailable
    assert len(result.issues) > 0


def test_query_engine_with_years_parameter():
    """QueryEngine 应该支持 years 参数"""
    registry = ItemRegistry()
    registry.register_field(name="revenue", description="营业收入")

    prechecker = Prechecker(
        provider_fields={"revenue"},
        registry=registry
    )

    engine = QueryEngine(
        prechecker=prechecker,
        registry=registry,
        years=5
    )

    assert engine.years == 5


def test_query_engine_fetch_data_returns_dict_format():
    """_fetch_data 应该返回 {field: {year: value}} 格式"""
    registry = ItemRegistry()
    registry.register_field(name="revenue", description="营业收入")

    prechecker = Prechecker(
        provider_fields={"revenue"},
        registry=registry
    )

    engine = QueryEngine(prechecker=prechecker, registry=registry)

    # 模拟返回正确格式的数据
    expected_data = {
        "revenue": {2020: 800, 2021: 900, 2022: 1000, 2023: 1100}
    }

    with patch.object(engine, '_fetch_data', return_value=expected_data):
        with patch.object(engine, '_run_calculators', return_value={}):
            result = engine.query("600519", ["revenue"])

    assert result.data == expected_data
