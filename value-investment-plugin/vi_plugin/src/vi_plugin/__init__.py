"""
VI Plugin
=========
Value Investment Plugin for Acorn.

This plugin acts as a thin wrapper around vi_core, exposing its functionality
to the Acorn system.
"""

from acorn_core import Task, hookimpl

# Import vi_core plugin for delegation
from vi_core import plugin as vi_core_plugin


class VIPlugin:
    """Value Investment Plugin - 桥接 VI Core 到 Acorn"""

    SUPPORTED_COMMANDS = ["vi_query", "vi_list_fields", "vi_list_calculators"]

    def __init__(self) -> None:
        self._vi_core = vi_core_plugin

    @property
    def commands(self) -> list[str]:
        return self.SUPPORTED_COMMANDS

    @hookimpl
    def handle(self, task: Task) -> dict:
        """Delegate to vi_core plugin"""
        command = task.command

        # Check if command is supported
        if command not in self.SUPPORTED_COMMANDS:
            return {"success": False, "error": {"code": "NOT_IMPLEMENTED"}}

        result = self._vi_core.handle(task)

        # Normalize error format if needed
        if not result.get("success") and isinstance(result.get("error"), str):
            result = {
                "success": False,
                "error": {"code": "NOT_IMPLEMENTED", "message": result["error"]},
            }

        return result


plugin = VIPlugin()
