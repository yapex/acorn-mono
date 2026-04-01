"""Test Query Engine - 统一查询接口"""
from unittest.mock import MagicMock, patch
from vi_core.query import QueryEngine, QueryResult
from vi_core.precheck import Prechecker, PrecheckResult
from vi_core.items import ItemRegistry


def test_query_engine_basic():
    """QueryEngine 应该能创建"""
    engine = QueryEngine()
    assert engine is not None


def test_query_result_dataclass():
    """QueryResult 应该正确存储数据"""
    result = QueryResult(
        success=True,
        symbol="600519",
        data={"revenue": {2023: 1000}},
        available=["revenue"],
        unavailable=[],
        issues=[],
    )

    assert result.success is True
    assert result.symbol == "600519"
    assert result.data["revenue"][2023] == 1000


def test_query_with_successful_precheck():
    """预检成功时查询应该继续执行"""
    registry = ItemRegistry()
    registry.register_field(name="revenue", description="营业收入")

    prechecker = Prechecker(
        provider_fields={"revenue"},
        registry=registry
    )

    engine = QueryEngine(prechecker=prechecker, registry=registry)

    # 模拟 _fetch_data 返回数据
    with patch.object(engine, '_fetch_data', return_value={"revenue": {2023: 1000}}):
        result = engine.query("600519", ["revenue"])

    assert result.success is True
    assert "revenue" in result.available


def test_query_with_failed_precheck():
    """预检失败时查询应该返回失败结果"""
    registry = ItemRegistry()
    registry.register_field(name="revenue", description="营业收入")

    prechecker = Prechecker(
        provider_fields=set(),  # 没有可用字段
        registry=registry
    )

    engine = QueryEngine(prechecker=prechecker, registry=registry)

    result = engine.query("600519", ["revenue"])

    assert result.success is False
    assert "revenue" in result.unavailable
    assert len(result.issues) > 0


def test_query_result_contains_precheck_info():
    """QueryResult 应该包含预检信息"""
    registry = ItemRegistry()
    registry.register_field(name="revenue", description="营业收入")

    prechecker = Prechecker(
        provider_fields={"revenue"},
        registry=registry
    )

    engine = QueryEngine(prechecker=prechecker, registry=registry)

    with patch.object(engine, '_fetch_data', return_value={"revenue": {2023: 1000}}):
        result = engine.query("600519", ["revenue"])

    assert result.precheck is not None
    assert result.precheck.success is True


def test_query_mixed_items():
    """混合可用/不可用 items"""
    registry = ItemRegistry()
    registry.register_field(name="revenue", description="营业收入")
    registry.register_field(name="net_profit", description="净利润")

    prechecker = Prechecker(
        provider_fields={"revenue"},  # 只有 revenue 可用
        registry=registry
    )

    engine = QueryEngine(prechecker=prechecker, registry=registry)

    with patch.object(engine, '_fetch_data', return_value={"revenue": {2023: 1000}}):
        result = engine.query("600519", ["revenue", "net_profit"])

    assert "revenue" in result.available
    assert "net_profit" in result.unavailable


def test_query_engine_internal_precheck():
    """QueryEngine 内部应该调用 prechecker.check"""
    registry = ItemRegistry()
    registry.register_field(name="revenue", description="营业收入")

    mock_prechecker = MagicMock()
    mock_prechecker.check.return_value = PrecheckResult(
        available=["revenue"],
        issues=[],
        symbol="600519"
    )

    engine = QueryEngine(prechecker=mock_prechecker, registry=registry)

    with patch.object(engine, '_fetch_data', return_value={}):
        engine.query("600519", ["revenue"])

    mock_prechecker.check.assert_called_once_with("600519", ["revenue"])
