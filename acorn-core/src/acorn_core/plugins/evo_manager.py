"""
EvoManager - 进化管理器
=======================
系统的"求生欲"——痛觉反馈、错误追踪、能力盘点。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pluggy
from acorn_core.specs import hookimpl

if TYPE_CHECKING:
    from acorn_events import EventBus


class EvoManager:
    """
    进化管理器 - 赋予 Acorn 求生欲的干细胞插件

    Args:
        pm: PluginManager 实例（必须，用于调用 Hook）
        event_bus: 事件总线实例（可选，用于订阅事件）
    """

    def __init__(
        self,
        pm: pluggy.PluginManager,
        event_bus: EventBus | None = None,
    ) -> None:
        self._pm = pm  # 必须依赖：用于调用 Hook
        self._event_bus = event_bus  # 可选依赖：用于订阅事件
        self.error_log: list[dict[str, Any]] = []
        self.max_log = 100
        self.capability_missing: list[dict[str, Any]] = []  # 能力缺失（通用）

    def _get_default_event_bus(self) -> EventBus:
        """获取默认事件总线（延迟导入避免循环依赖）"""
        from acorn_events import EventBus
        return EventBus()

    def _get_evolution_spec(
        self,
        capability_type: str,
        name: str,
        context: dict | None = None,
    ) -> str | None:
        """
        获取进化规范

        通过遍历已注册的插件，查找实现了 get_evolution_spec 方法的插件。
        
        注意：由于插件架构设计（vi_core 使用独立的 PluginManager），
        无法通过 pluggy Hook 直接调用。此方法通过直接方法调用实现。

        Args:
            capability_type: 能力类型，如 "calculator", "field"
            name: 能力名称
            context: 上下文信息

        Returns:
            None - 没有插件能提供进化规范
            str - 进化规范（给 LLM 的 prompt）
        """
        # 遍历所有插件，查找实现 get_evolution_spec 的
        for plugin in self._pm.get_plugins():
            if hasattr(plugin, "get_evolution_spec"):
                try:
                    spec = plugin.get_evolution_spec(capability_type, name, context)
                    if spec:
                        return spec
                except Exception:
                    pass

        # 如果 PluginManager 中没有，尝试从 vi_core 获取
        # 通过遍历所有插件查找
        return self._find_evolution_spec_from_plugins(
            capability_type, name, context
        )

    def _find_evolution_spec_from_plugins(
        self,
        capability_type: str,
        name: str,
        context: dict | None = None,
    ) -> str | None:
        """
        从所有已加载的插件中查找进化规范
        
        遍历所有插件的子插件管理器（如 vi_core 的 PluginManager）
        """
        # 尝试从 vi_core 的 ViCorePlugin 获取
        vi_core_plugin = self._find_plugin_by_name("vi")
        if vi_core_plugin and hasattr(vi_core_plugin, "_find_evolution_spec"):
            try:
                return vi_core_plugin._find_evolution_spec(
                    capability_type, name, context
                )
            except Exception:
                pass

        return None

    def _find_plugin_by_name(self, name: str) -> Any:
        """根据名称查找插件"""
        for plugin_name, plugin in self._pm.list_name_plugin():
            if plugin_name == name or plugin_name.endswith(f".{name}"):
                return plugin
        return None

    def _on_capability_missing(self, event_type: str, sender: Any, **kwargs: Any) -> None:
        """
        订阅 evo.capability.missing 事件
        
        这是通用的能力缺失事件，不关心具体业务类型
        payload: capability_type, name, context, sender
        """
        capability_type = kwargs.get("capability_type", "unknown")
        name = kwargs.get("name", "unknown")
        context = kwargs.get("context", {})

        # 记录能力缺失
        self.capability_missing.append({
            "capability_type": capability_type,
            "name": name,
            "context": context,
            "sender": str(sender),
        })
        if len(self.capability_missing) > self.max_log:
            self.capability_missing = self.capability_missing[-self.max_log:]

        # 通过 Hook 获取进化规范
        spec = self._get_evolution_spec(capability_type, name, context)

        if spec:
            # 打印进化规范（供 LLM 读取）
            print(f"\n{'='*60}")
            print(f"EVOLUTION_NEEDED: {capability_type}/{name}")
            print(f"{'='*60}")
            print(spec)
            print(f"{'='*60}\n")
        else:
            # 没有插件能提供进化规范
            print(f"\n{'='*60}")
            print(f"EVO_CAPABILITY_MISSING: {capability_type}/{name}")
            print("没有插件能提供进化规范")
            print(f"{'='*60}\n")

    @property
    def commands(self) -> list[str]:
        """声明支持的命令"""
        return ["capabilities", "error_log"]

    @hookimpl
    def get_capabilities(self) -> dict[str, Any]:
        """声明能力清单"""
        return {
            "commands": ["capabilities", "error_log"],
            "args": {}
        }

    def vi_status(self) -> dict[str, Any]:
        """返回 EvoManager 状态"""
        return {
            "name": "evo_manager",
            "description": "Evolution Manager - 进化管理器，追踪系统能力缺口",
            "version": "1.0.0",
            "capabilities": {
                "capability_missing_count": len(self.capability_missing),
            },
            "recent_capability_missing": self.capability_missing[-5:],
        }

    @hookimpl
    def on_load(self) -> None:
        """初始化 EvoManager"""
        # 延迟初始化事件总线
        if self._event_bus is None:
            self._event_bus = self._get_default_event_bus()

        # 订阅系统级演化事件
        from acorn_events import AcornEvents
        self._event_bus.on(AcornEvents.EVO_CAPABILITY_MISSING)(self._on_capability_missing)

    @hookimpl
    def handle(self, task: Any) -> dict[str, Any]:
        """处理系统命令"""
        command = task.command

        if command == "capabilities":
            return {"success": True, "data": self._get_capabilities_report()}
        elif command == "error_log":
            return {"success": True, "data": self._get_error_report()}

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
            "能力缺失追踪:",
            f"  - capability_missing: {len(self.capability_missing)} 条记录",
            "",
            "总计：2 个系统命令",
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
        lines.append(f"总计：{len(self.error_log)} 条错误记录")

        return "\n".join(lines)

    @hookimpl
    def on_unload(self) -> None:
        """卸载清理"""
        pass


# 注意：EvoManager 不再通过 entry_points 加载
# Kernel 会在 load_plugins() 中直接实例化并注册 EvoManager
# 因此不再导出 plugin 单例
