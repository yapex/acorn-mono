"""
EvoManager - 进化管理器
=======================
系统的"求生欲"——痛觉反馈、错误追踪、能力盘点。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from acorn_core.specs import hookimpl

if TYPE_CHECKING:
    from acorn_events import EventBus, AcornEvents


class EvoManager:
    """
    进化管理器 - 赋予 Acorn 求生欲的干细胞插件

    Args:
        event_bus: 事件总线实例（IOC: 通过依赖注入获得）
    """

    def __init__(self, event_bus: EventBus | None = None) -> None:
        self.error_log: list[dict[str, Any]] = []
        self.max_log = 100
        self.unsupported_fields: list[dict[str, Any]] = []  # 系统标准字段定义中没有
        self.unfilled_fields: list[dict[str, Any]] = []  # 标准字段中但 Provider 不支持或返回空
        self.extension_requests: list[dict[str, Any]] = []  # Calculator 扩展请求
        self._event_bus = event_bus  # IOC: 由外部注入或延迟初始化

    def _get_default_event_bus(self) -> EventBus:
        """获取默认事件总线（延迟导入避免循环依赖）"""
        from acorn_events import EventBus
        return EventBus()

    def _on_field_unsupported(self, event_type: str, sender: Any, **kwargs: Any) -> None:
        """订阅 vi.field.unsupported 事件，记录系统不支持的字段"""
        symbol = kwargs.get("symbol", "unknown")
        fields = kwargs.get("fields", [])
        self.unsupported_fields.append({
            "symbol": symbol,
            "fields": fields
        })
        # 保持最大记录数
        if len(self.unsupported_fields) > self.max_log:
            self.unsupported_fields = self.unsupported_fields[-self.max_log:]

    def _on_field_unfilled(self, event_type: str, sender: Any, **kwargs: Any) -> None:
        """订阅 vi.field.unfilled 事件，记录 Provider 无法提供的字段"""
        symbol = kwargs.get("symbol", "unknown")
        fields = kwargs.get("fields", [])
        self.unfilled_fields.append({
            "symbol": symbol,
            "fields": fields
        })
        # 保持最大记录数
        if len(self.unfilled_fields) > self.max_log:
            self.unfilled_fields = self.unfilled_fields[-self.max_log:]

    def _on_calculator_extension_needed(self, event_type: str, sender: Any, **kwargs: Any) -> None:
        """订阅 calculator.extension_needed 事件，打印扩展 Prompt 给 LLM Agent"""
        calculator_name = kwargs.get("calculator_name", "unknown")
        extension_prompt = kwargs.get("extension_prompt", "")

        # 记录请求
        self.extension_requests.append({
            "calculator_name": calculator_name,
            "extension_prompt": extension_prompt,
        })
        if len(self.extension_requests) > self.max_log:
            self.extension_requests = self.extension_requests[-self.max_log:]

        # 直接打印给 LLM Agent
        print(f"\n{'='*60}")
        print(f"need: calculator_creation")
        print(f"calculator_name: {calculator_name}")
        print(f"{'='*60}")
        print(extension_prompt)
        print(f"{'='*60}\n")

    @property
    def commands(self) -> list[str]:
        """声明支持的命令"""
        return ["capabilities", "error_log", "extension_prompts"]

    @hookimpl
    def get_capabilities(self) -> dict[str, Any]:
        """声明能力清单"""
        return {
            "commands": ["capabilities", "error_log", "extension_prompts"],
            "args": {}
        }

    def vi_status(self) -> dict[str, Any]:
        """返回 EvoManager 状态"""
        return {
            "name": "evo_manager",
            "description": "Evolution Manager - 进化管理器，追踪系统能力缺口",
            "version": "1.0.0",
            "capabilities": {
                "extension_requests": len(self.extension_requests),
                "unsupported_fields": len(self.unsupported_fields),
                "unfilled_fields": len(self.unfilled_fields),
            },
            "recent_extension_requests": [
                {"calculator_name": req.get("calculator_name", "unknown")}
                for req in self.extension_requests[-5:]
            ],
        }

    @hookimpl
    def on_load(self) -> None:
        """初始化 EvoManager"""
        # 延迟初始化事件总线
        if self._event_bus is None:
            self._event_bus = self._get_default_event_bus()

        self.error_log = []
        
        # 使用事件常量订阅
        from acorn_events import AcornEvents
        self._event_bus.on(AcornEvents.FIELD_UNSUPPORTED)(self._on_field_unsupported)
        self._event_bus.on(AcornEvents.FIELD_UNFILLED)(self._on_field_unfilled)
        self._event_bus.on(AcornEvents.CALCULATOR_EXTENSION_NEEDED)(self._on_calculator_extension_needed)

    @hookimpl
    def handle(self, task: Any) -> dict[str, Any]:
        """处理系统命令"""
        command = task.command

        if command == "capabilities":
            return {"success": True, "data": self._get_capabilities_report()}
        elif command == "error_log":
            return {"success": True, "data": self._get_error_report()}
        elif command == "extension_prompts":
            return {"success": True, "data": self._get_extension_prompts()}

        return {
            "success": False,
            "error": {
                "code": "NOT_IMPLEMENTED",
                "message": f"Unknown command: {command}"
            }
        }

    def _get_capabilities_report(self) -> str:
        """生成能力报告"""
        lines = [
            "📋 系统能力报告",
            "=" * 40,
            "",
            "可用命令:",
            "  - capabilities (当前命令)",
            "  - error_log",
            "",
            "字段追踪:",
            f"  - unsupported_fields: {len(self.unsupported_fields)} 条记录",
            f"  - unfilled_fields: {len(self.unfilled_fields)} 条记录",
            "",
            "总计: 2 个系统命令",
            "=" * 40,
        ]
        return "\n".join(lines)

    def _get_error_report(self) -> str:
        """生成错误日志报告"""
        if not self.error_log:
            return "✅ 暂无错误记录"

        lines = [
            "📋 错误日志报告",
            "=" * 40,
            "",
        ]

        for i, err in enumerate(reversed(self.error_log[-10:]), 1):
            lines.append(f"{i}. [{err['error_type']}] {err.get('task', 'N/A')}")
            lines.append(f"   {err['error_message'][:60]}...")
            lines.append("")

        lines.append("=" * 40)
        lines.append(f"总计: {len(self.error_log)} 条错误记录")

        return "\n".join(lines)

    def _get_extension_prompts(self) -> dict[str, Any]:
        """获取 Calculator 扩展请求的 Prompt 列表"""
        return {
            "count": len(self.extension_requests),
            "prompts": [
                {
                    "calculator_name": req["calculator_name"],
                    "extension_prompt": req["extension_prompt"],
                    "symbol": req.get("symbol", "unknown"),
                }
                for req in self.extension_requests[-10:]  # 最近 10 条
            ]
        }

    @hookimpl
    def on_unload(self) -> None:
        """卸载清理"""
        pass


# 导出单例
plugin = EvoManager()
