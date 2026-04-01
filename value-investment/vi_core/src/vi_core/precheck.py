"""Prechecker - 查询前可用性检查

在真正执行查询前检查：
1. 请求的 items 是否都存在
2. Calculator 的依赖是否都能满足
3. 返回友好的问题诊断
"""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum

from .items import ItemRegistry, ItemSource


class IssueSeverity(Enum):
    """问题严重程度"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class Issue:
    """问题描述"""
    item: str
    severity: IssueSeverity
    reason: str
    suggestion: str = ""
    missing_fields: list[str] = field(default_factory=list)
    # 来源：导致这个问题的 item 类型，用于区分能力缺失类型
    source: ItemSource | None = None


@dataclass
class PrecheckResult:
    """预检结果"""
    available: list[str]          # 可用的 items
    issues: list[Issue]            # 问题列表
    symbol: str = ""               # 查询的股票代码

    @property
    def success(self) -> bool:
        """是否完全成功"""
        return len(self.issues) == 0

    @property
    def has_errors(self) -> bool:
        """是否有错误级别的问题"""
        return any(i.severity == IssueSeverity.ERROR for i in self.issues)

    def format(self) -> list[str]:
        """格式化输出为行列表"""
        lines = []

        if self.success:
            lines.append(f"✅ {self.symbol}: 所有 {len(self.available)} 个数据项可用")
            if self.available:
                lines.append(f"   可用数据项: {', '.join(self.available)}")
        else:
            lines.append(f"⚠️  {self.symbol}: {len(self.available)}/{len(self.available) + len(self.issues)} 可用")
            if self.available:
                lines.append(f"   可用: {', '.join(self.available)}")

        if self.issues:
            lines.append("")
            lines.append("📋 问题诊断：")
            for issue in self.issues:
                severity_icon = "❌" if issue.severity == IssueSeverity.ERROR else "⚠️"
                lines.append(f"  {severity_icon} {issue.item}")
                lines.append(f"     原因: {issue.reason}")
                if issue.suggestion:
                    lines.append(f"     建议: {issue.suggestion}")

        return lines

    def format_table(self) -> str:
        """表格格式输出
        
        使用简单的文本表格格式，不依赖外部库
        """
        lines = []

        # Header
        lines.append(f"{'数据项':<30} {'状态':<10} {'说明':<40}")
        lines.append("─" * 80)

        # Available items
        for item in self.available:
            lines.append(f"{item:<30} {'✅':<10} {'可用'}")

        # Issues
        for issue in self.issues:
            severity = "❌" if issue.severity == IssueSeverity.ERROR else "⚠️"
            lines.append(f"{issue.item:<30} {severity:<10} {issue.reason[:40]}")

        return "\n".join(lines)

    def __str__(self) -> str:
        """字符串表示"""
        return "\n".join(self.format())


class Prechecker:
    """预检器"""

    def __init__(
        self,
        provider_fields: set[str] | None = None,
        calculator_requires: dict[str, list[str]] | None = None,
        registry: ItemRegistry | None = None,
    ):
        """
        Args:
            provider_fields: Provider 能提供的字段集合
            calculator_requires: Calculator name -> [required fields] 映射（已废弃，使用 registry）
            registry: Item 注册表
        """
        self._provider_fields = provider_fields or set()
        self._calculator_requires = calculator_requires or {}
        self._registry = registry or ItemRegistry()

    def check(self, symbol: str, items: list[str]) -> PrecheckResult:
        """检查 items 的可用性
        
        Args:
            symbol: 股票代码
            items: 要查询的 items 列表
            
        Returns:
            PrecheckResult: 包含可用 items 和问题列表
        """
        available = []
        issues = []

        for item_name in items:
            item = self._registry.get(item_name)

            if item is None:
                # Item 不存在于注册表 - 视为 field 缺失（系统不认识这个能力）
                issues.append(Issue(
                    item=item_name,
                    severity=IssueSeverity.ERROR,
                    reason=f"未知的数据项: {item_name}",
                    suggestion="使用 'vi list' 查看可用的数据项",
                    source=None,  # 未知类型
                ))
                continue

            if item.source == ItemSource.FIELD:
                # Field 类型：检查 Provider 是否支持
                if item_name in self._provider_fields:
                    available.append(item_name)
                else:
                    issues.append(Issue(
                        item=item_name,
                        severity=IssueSeverity.ERROR,
                        reason=f"当前市场不支持: {item_name}",
                        suggestion="使用 'vi list' 查看支持的数据项",
                        source=ItemSource.FIELD,
                    ))

            elif item.source == ItemSource.CALCULATOR:
                # Calculator 类型：检查依赖是否满足
                missing = self._check_calculator_deps(item_name, item.requires)

                if missing:
                    issues.append(Issue(
                        item=item_name,
                        severity=IssueSeverity.ERROR,
                        reason=f"缺少依赖字段: {', '.join(missing)}",
                        missing_fields=missing,
                        suggestion=f"无法计算 {item_name}，因为 {', '.join(missing)} 不可用",
                        source=ItemSource.CALCULATOR,
                    ))
                else:
                    available.append(item_name)

        # 发现问题时发布 Evolution 事件
        self._publish_evolution_events(symbol, items, issues)

        return PrecheckResult(
            available=available,
            issues=issues,
            symbol=symbol,
        )

    def _publish_evolution_events(
        self,
        symbol: str,
        original_items: list[str],
        issues: list[Issue],
    ) -> None:
        """发布 Evolution 事件
        
        当预检发现问题时，为每个缺失的 item 发布 CapabilityMissingEvent。
        这些事件可以被未来的 LLM Agent 处理。
        """
        from .evolution import (
            publish_capability_missing,
            CapabilityType,
            CapabilityReason,
        )

        for issue in issues:
            if issue.severity == IssueSeverity.ERROR:
                # 根据 source 确定 capability_type
                if issue.source == ItemSource.CALCULATOR:
                    capability_type = CapabilityType.CALCULATOR
                    # 计算器依赖缺失
                    reason = CapabilityReason.CALC_REQUIRES_MISSING
                elif issue.source == ItemSource.FIELD:
                    capability_type = CapabilityType.FIELD
                    reason = CapabilityReason.FIELD_UNFILLED
                else:
                    # source is None (未知类型)
                    capability_type = CapabilityType.FIELD
                    reason = CapabilityReason.FIELD_UNSUPPORTED

                publish_capability_missing(
                    item=issue.item,
                    capability_type=capability_type,
                    reason=reason,
                    missing_fields=issue.missing_fields,
                    context={
                        "symbol": symbol,
                        "query_items": original_items,
                    },
                )

    def _check_calculator_deps(self, name: str, requires: list[str]) -> list[str]:
        """检查 Calculator 依赖是否都满足
        
        Returns:
            缺失的字段列表，空列表表示全部满足
        """
        missing = []

        for dep in requires:
            # 检查依赖是否是 Field 且 Provider 支持
            dep_item = self._registry.get(dep)

            if dep_item is None:
                missing.append(dep)
            elif dep_item.source == ItemSource.FIELD:
                if dep not in self._provider_fields:
                    missing.append(dep)
            elif dep_item.source == ItemSource.CALCULATOR:
                # 依赖也是 Calculator，递归检查
                sub_missing = self._check_calculator_deps(dep, dep_item.requires)
                missing.extend(sub_missing)

        return list(set(missing))  # 去重
