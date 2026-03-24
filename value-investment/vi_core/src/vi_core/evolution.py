"""Evolution 接口预留

为未来 Agent 能力预留的接口：
- 当预检发现缺失时，发布 Evolution 事件
- 事件携带完整上下文，供 Agent 处理

能力类型 (capability_type):
- calculator: 计算器缺失（系统没有这个计算器）
- field: 字段缺失（系统没有这个字段或 Provider 不支持）

进化规则可以按 capability_type 匹配：
- "calculator" → 触发创建计算器
- "field" → 触发添加字段支持
"""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class CapabilityType(Enum):
    """能力类型"""
    CALCULATOR = "calculator"  # 计算器能力
    FIELD = "field"           # 字段能力


class CapabilityReason(Enum):
    """能力缺失原因"""
    # Calculator reasons
    CALC_NOT_FOUND = "calc_not_found"           # 计算器不存在
    CALC_REQUIRES_MISSING = "calc_requires_missing"  # 计算器依赖不满足
    
    # Field reasons
    FIELD_UNSUPPORTED = "field_unsupported"     # 系统不支持此字段
    FIELD_UNFILLED = "field_unfilled"          # 系统支持但 Provider 不提供


@dataclass
class EvolutionEvent:
    """Evolution 事件基类"""
    event_type: str


@dataclass
class CapabilityMissingEvent(EvolutionEvent):
    """能力缺失事件
    
    当预检发现缺失时发布此事件，供 Agent 处理。
    
    事件会区分：
    - capability_type: calculator | field
    - reason: 具体原因
    """
    event_type: str = "capability_missing"
    
    # 能力类型：calculator 或 field
    capability_type: CapabilityType = CapabilityType.FIELD
    
    # 具体的原因
    reason: CapabilityReason = CapabilityReason.FIELD_UNSUPPORTED
    
    # 缺失的数据项名称（单个）
    item: str = ""
    
    # 缺失的依赖字段列表（用于计算器场景）
    missing_fields: list[str] = field(default_factory=list)
    
    # 额外的上下文信息
    context: dict[str, Any] = field(default_factory=dict)
    
    def to_prompt(self) -> str:
        """生成给 LLM Agent 的提示
        
        包含足够的信息让 Agent 能够：
        1. 理解问题
        2. 决定如何解决
        3. 与用户交互
        """
        prompt_parts = [
            "## 能力缺失报告",
            "",
            f"**能力类型**: {self.capability_type.value}",
            f"**缺失项**: {self.item}",
            f"**原因**: {self.reason.value}",
        ]
        
        if self.missing_fields:
            prompt_parts.append(f"**缺失依赖**: {', '.join(self.missing_fields)}")
        
        if self.context:
            prompt_parts.append("")
            prompt_parts.append("**上下文**:")
            for key, value in self.context.items():
                if key == "unsupported":
                    prompt_parts.append(f"- 系统不支持的字段: {value}")
                elif key == "unfilled":
                    prompt_parts.append(f"- Provider 不支持的字段: {value}")
                elif key == "query_items":
                    prompt_parts.append(f"- 请求的数据项: {value}")
                elif key == "symbol":
                    prompt_parts.append(f"- 股票代码: {value}")
                else:
                    prompt_parts.append(f"- {key}: {value}")
        
        # 根据 capability_type 提供不同的行动建议
        if self.capability_type == CapabilityType.CALCULATOR:
            prompt_parts.extend([
                "",
                "## 可选行动",
                "",
                "1. **创建 Calculator**: 实现一个计算器来满足这个能力",
                "2. **告知用户**: 提供替代方案",
                "3. **忽略**: 如果问题无法自动解决",
            ])
        else:  # FIELD
            prompt_parts.extend([
                "",
                "## 可选行动",
                "",
                "1. **扩展 Provider**: 添加新的数据源支持此字段",
                "2. **创建 Calculator**: 如果此字段可以通过计算获得",
                "3. **告知用户**: 提供替代方案",
                "4. **忽略**: 如果问题无法自动解决",
            ])
        
        prompt_parts.append("")
        prompt_parts.append("请决定如何处理此问题。")
        
        return "\n".join(prompt_parts)
    
    def to_event_dict(self) -> dict[str, Any]:
        """转换为事件总线所需的 dict 格式"""
        return {
            "event_type": self.event_type,
            "capability_type": self.capability_type.value,
            "reason": self.reason.value,
            "item": self.item,
            "missing_fields": self.missing_fields,
            "context": self.context,
        }


def publish_capability_missing(
    item: str,
    capability_type: CapabilityType,
    reason: CapabilityReason,
    missing_fields: list[str] | None = None,
    context: dict[str, Any] | None = None,
) -> CapabilityMissingEvent:
    """发布能力缺失事件
    
    Args:
        item: 缺失的数据项名称
        capability_type: 能力类型 (CALCULATOR | FIELD)
        reason: 具体原因
        missing_fields: 缺失的依赖字段列表
        context: 额外上下文信息
        
    Returns:
        创建的 CapabilityMissingEvent 事件
    """
    event = CapabilityMissingEvent(
        item=item,
        capability_type=capability_type,
        reason=reason,
        missing_fields=missing_fields or [],
        context=context or {},
    )
    
    # TODO: 发布到事件总线
    # event_bus.publish(AcornEvents.EVO_CAPABILITY_MISSING, **event.to_event_dict())
    
    # 目前只打印日志
    try:
        from loguru import logger
        logger = logger
        logger.warning(
            f"Capability missing: type={capability_type.value}, item={item}, "
            f"reason={reason.value}, missing={missing_fields}"
        )
    except ImportError:
        import logging
        logging.warning(
            f"Capability missing: type={capability_type.value}, item={item}, "
            f"reason={reason.value}, missing={missing_fields}"
        )
    
    return event