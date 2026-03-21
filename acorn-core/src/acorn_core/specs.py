"""
物理法则 (The Genes)
====================
定义系统的核心协议。插件必须实现这些钩子。
"""

from __future__ import annotations

from typing import Optional

import pluggy

hookspec = pluggy.HookspecMarker("evo")
hookimpl = pluggy.HookimplMarker("evo")


class CommandHandler:
    """
    命令处理 trait (核心)

    实现此 trait 的插件可以处理命令。
    """

    @hookspec
    def commands(self) -> list[str]:
        """
        声明支持的命令列表

        Returns:
            命令名列表，如 ["echo", "greet"]
        """
        return []

    @hookspec
    def handle(self, task) -> dict:
        """
        处理任务

        Args:
            task: Task 对象

        Returns:
            执行结果 dict，包含:
            - success: bool
            - data: Any (成功时)
            - error: dict (失败时), 包含 code 和 message
        """
        return {
            "success": False,
            "error": {"code": "NOT_IMPLEMENTED", "message": "Not implemented"}
        }


class CapabilityProvider:
    """能力声明 trait"""

    @hookspec
    def get_capabilities(self) -> Optional[dict]:
        """
        声明能力清单

        Returns:
            能力描述 dict，包含:
            - commands: list[str] - 命令列表
            - args: dict - 参数规范
        """
        return None


class LoadCapable:
    """加载 lifecycle trait"""

    @hookspec
    def on_load(self):
        """插件加载时调用"""
        pass


class UnloadCapable:
    """卸载 lifecycle trait"""

    @hookspec
    def on_unload(self):
        """插件卸载时调用"""
        pass


class Genes(
    CommandHandler,
    CapabilityProvider,
    LoadCapable,
    UnloadCapable,
):
    """
    生命体的基因 - 定义系统可扩展的核心协议
    """
    pass
