"""Test Evolution Event Interface"""
from vi_core.evolution import (
    CapabilityMissingEvent,
    CapabilityType,
    CapabilityReason,
    publish_capability_missing,
)


def test_capability_missing_event_structure():
    """能力缺失事件应该包含完整上下文"""
    event = CapabilityMissingEvent(
        item="implied_growth",
        capability_type=CapabilityType.CALCULATOR,
        reason=CapabilityReason.CALC_REQUIRES_MISSING,
        missing_fields=["operating_cash_flow"],
        context={"symbol": "00700", "market": "HK"}
    )

    assert event.item == "implied_growth"
    assert event.capability_type == CapabilityType.CALCULATOR
    assert "operating_cash_flow" in event.missing_fields
    assert event.context["symbol"] == "00700"
    assert event.context["market"] == "HK"


def test_evolution_event_to_prompt():
    """应该能生成给 LLM 的 prompt"""
    event = CapabilityMissingEvent(
        item="implied_growth",
        capability_type=CapabilityType.CALCULATOR,
        reason=CapabilityReason.CALC_REQUIRES_MISSING,
        missing_fields=["operating_cash_flow"],
        context={"symbol": "00700", "market": "HK"}
    )

    prompt = event.to_prompt()

    assert "implied_growth" in prompt
    assert "operating_cash_flow" in prompt
    assert "00700" in prompt
    assert "calculator" in prompt  # capability_type 应该显示


def test_evolution_event_to_dict():
    """应该能转换为 dict 格式"""
    event = CapabilityMissingEvent(
        item="implied_growth",
        capability_type=CapabilityType.CALCULATOR,
        reason=CapabilityReason.CALC_REQUIRES_MISSING,
        missing_fields=["operating_cash_flow"],
        context={"symbol": "00700"}
    )

    event_dict = event.to_event_dict()

    assert event_dict["event_type"] == "capability_missing"
    assert event_dict["capability_type"] == "calculator"
    assert event_dict["item"] == "implied_growth"
    assert event_dict["reason"] == "calc_requires_missing"
    assert "operating_cash_flow" in event_dict["missing_fields"]


def test_publish_capability_missing():
    """publish_capability_missing 应该能创建并发布事件"""
    event = publish_capability_missing(
        item="test_item",
        capability_type=CapabilityType.FIELD,
        reason=CapabilityReason.FIELD_UNFILLED,
        missing_fields=["field1", "field2"],
        context={"symbol": "600519"}
    )

    assert event is not None
    assert event.item == "test_item"
    assert event.capability_type == CapabilityType.FIELD


def test_evolution_event_default_type():
    """EvolutionEvent 子类应该有默认 event_type"""
    event = CapabilityMissingEvent(
        item="test",
        capability_type=CapabilityType.FIELD,
        reason=CapabilityReason.FIELD_UNSUPPORTED,
        missing_fields=[],
        context={}
    )

    assert event.event_type == "capability_missing"


def test_prompt_differs_by_capability_type():
    """不同 capability_type 应该生成不同的 prompt"""
    calc_event = CapabilityMissingEvent(
        item="implied_growth",
        capability_type=CapabilityType.CALCULATOR,
        reason=CapabilityReason.CALC_REQUIRES_MISSING,
        missing_fields=["operating_cash_flow"],
        context={}
    )

    field_event = CapabilityMissingEvent(
        item="revenue",
        capability_type=CapabilityType.FIELD,
        reason=CapabilityReason.FIELD_UNFILLED,
        missing_fields=["revenue"],
        context={}
    )

    calc_prompt = calc_event.to_prompt()
    field_prompt = field_event.to_prompt()

    # Calculator prompt 应该提到"创建 Calculator"
    assert "创建 Calculator" in calc_prompt
    # Field prompt 应该提到"扩展 Provider"
    assert "扩展 Provider" in field_prompt
