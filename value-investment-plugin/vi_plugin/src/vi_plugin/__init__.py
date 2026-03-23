"""
VI Plugin
=========
Value Investment Plugin for Acorn.
"""

from acorn_core import Task, hookimpl


class VIPlugin:
    """Value Investment Plugin - 桥接 VI Core 到 Acorn"""

    @property
    def commands(self) -> list[str]:
        return ["vi_query", "vi_list_fields", "vi_list_calculators"]

    @hookimpl
    def handle(self, task: Task) -> dict:
        command = task.command
        args = task.args or {}

        if command == "vi_query":
            return self._handle_query(args)
        elif command == "vi_list_fields":
            return self._handle_list_fields(args)
        elif command == "vi_list_calculators":
            return self._handle_list_calculators(args)

        return {"success": False, "error": {"code": "NOT_IMPLEMENTED"}}

    def _handle_query(self, args: dict) -> dict:
        """处理查询命令"""
        # TODO: 委托给 vi_core
        return {
            "success": True,
            "data": {
                "symbol": args.get("symbol"),
                "note": "VI query stub - vi_core integration pending"
            }
        }

    def _handle_list_fields(self, args: dict) -> dict:
        """列出可用字段"""
        # TODO: 委托给 vi_core
        return {"success": True, "data": []}

    def _handle_list_calculators(self, args: dict) -> dict:
        """列出可用计算器"""
        # TODO: 委托给 vi_core
        return {"success": True, "data": []}


plugin = VIPlugin()
