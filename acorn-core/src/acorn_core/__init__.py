"""
小橡子 (Acorn) - 自进化插件系统
===============================
基于 pluggy 的轻量级插件框架，支持自我进化。
"""

from .kernel import Acorn
from .models import TaskContext
from .plugins.sandbox import Sandbox, NamespaceSandbox, SubprocessSandbox, get_default_sandbox
from .specs import Genes, hookimpl, hookspec
from .types import Capabilities, ErrorInfo, Response, Task

__all__ = [
    "Acorn",
    "TaskContext",
    "Task",
    "Response",
    "ErrorInfo",
    "Capabilities",
    "Genes",
    "hookimpl",
    "hookspec",
    # Sandbox
    "Sandbox",
    "NamespaceSandbox",
    "SubprocessSandbox",
    "get_default_sandbox",
]
