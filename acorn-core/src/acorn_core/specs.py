"""
物理法则 (The Genes)
====================
定义系统的核心协议。插件必须实现这些钩子。
"""

from __future__ import annotations

from typing import Optional

import pluggy
from acorn_events import EvolutionSpec as EvolutionSpecInterface

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


# =============================================================================
# Evolution Hooks (框架级，业务无关)
# =============================================================================

class EvolutionSpec(EvolutionSpecInterface):
    """
    进化机制 Hook spec - 框架级通用协议
    
    当系统发现能力缺失时，通过此 Hook 询问所有插件：
    "你能提供这个能力的进化规范吗？"
    
    依赖方向：业务插件 → 框架核心（实现此 Hook）
    
    使用方式：
    1. acorn_core/kernel.py 添加此 Hookspec 到 PluginManager
    2. 业务插件（如 CalculatorEngine）实现此 Hook
    3. EvoManager 通过 pm.hook.get_evolution_spec() 调用
    """

    @hookspec(firstresult=True)
    def get_evolution_spec(
        self,
        capability_type: str,
        name: str,
        context: dict | None = None,
    ) -> str | None:
        """继承自 EvolutionSpecInterface，由 pluggy 添加装饰器"""
        return None
