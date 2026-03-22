"""
EvoManager - 进化管理器
=======================
系统的"求生欲"——痛觉反馈、错误追踪、能力盘点。
"""

from typing import Any

from acorn_core.events import EventBus
from acorn_core.specs import hookimpl


class EvoManager:
    """
    进化管理器 - 赋予 Acorn 求生欲的干细胞插件
    """

    def __init__(self) -> None:
        self.error_log: list[dict[str, Any]] = []
        self.max_log = 100
        self.missing_fields: list[dict[str, Any]] = []
        self._event_bus = EventBus()

    def _on_plugin_loaded(self, event_type, sender, **kwargs):
        """订阅 acorn.plugin.loaded 事件，记录插件信息"""
        plugin_name = kwargs.get("plugin_name", "unknown")
        plugin: Any = kwargs.get("plugin")
        # 检查插件是否有缺失字段的能力声明
        if plugin and hasattr(plugin, "get_capabilities"):
            try:
                caps = plugin.get_capabilities()
                if caps and isinstance(caps, dict):
                    # 记录插件声明的字段
                    pass
            except Exception:
                pass

    def _on_field_missing(self, event_type, sender, **kwargs):
        """订阅 vi.field.missing 事件，记录缺失的字段"""
        symbol = kwargs.get("symbol", "unknown")
        fields = kwargs.get("fields", [])
        self.missing_fields.append({
            "symbol": symbol,
            "fields": fields
        })
        # 保持最大记录数
        if len(self.missing_fields) > self.max_log:
            self.missing_fields = self.missing_fields[-self.max_log:]

    @property
    def commands(self) -> list[str]:
        """声明支持的命令"""
        return ["capabilities", "error_log"]

    @hookimpl
    def get_capabilities(self) -> dict:
        """声明能力清单"""
        return {
            "commands": ["capabilities", "error_log"],
            "args": {}
        }

    @hookimpl
    def on_load(self) -> None:
        """初始化 EvoManager"""
        self.error_log = []
        self._event_bus.on("acorn.plugin.loaded")(self._on_plugin_loaded)
        self._event_bus.on("vi.field.missing")(self._on_field_missing)

    @hookimpl
    def handle(self, task) -> dict:
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
        # 访问 Acorn 的能力列表
        from pathlib import Path
        plugin_dir = Path(__file__).parent
        # 列出所有插件文件
        _ = [
            f.stem for f in plugin_dir.glob("*.py")
            if f.stem not in ["__init__", "evo_manager"]
        ]

        lines = [
            "📋 系统能力报告",
            "=" * 40,
            "",
            "可用命令:",
            "  - capabilities (当前命令)",
            "  - error_log",
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

    @hookimpl
    def on_unload(self) -> None:
        """卸载清理"""
        pass


# 导出单例
plugin = EvoManager()
