"""
沙箱模块
========
提供代码执行的安全隔离。

设计原则：除了核心 (Acorn)，万物皆可拔插。
沙箱本身也是可拔插的，可以有多种实现。
"""

from __future__ import annotations

import builtins
from abc import ABC, abstractmethod
from typing import Any


class Sandbox(ABC):
    """
    沙箱抽象基类

    所有沙箱实现都必须继承此类并实现 execute 方法。

    示例:
        class MySandbox(Sandbox):
            def execute(self, code: str, globals_dict: dict) -> dict:
                # 在隔离环境中执行代码
                ...
    """

    @abstractmethod
    def execute(self, code: str, globals_dict: dict[str, Any]) -> dict[str, Any]:
        """
        在沙箱中执行代码

        Args:
            code: 要执行的 Python 代码字符串
            globals_dict: 额外的全局变量

        Returns:
            执行后的命名空间字典
        """
        ...


class NamespaceSandbox(Sandbox):
    """
    命名空间沙箱

    通过限制 builtins 实现安全隔离。
    速度快，但安全性有限（理论上可以访问一些受限资源）。
    """

    # 危险函数黑名单
    DANGEROUS_FUNCTIONS = frozenset([
        'eval',      # 动态执行代码
        'exec',      # 动态执行代码
        'compile',   # 动态编译代码
        'open',      # 文件操作
        'input',     # 输入读取
        'breakpoint', # 调试
        'exit',      # 退出程序
        'quit',      # 退出程序
    ])

    def __init__(self, allowed_builtins: list[str] | None = None):
        """
        Args:
            allowed_builtins: 可选的额外允许的 builtins 列表
        """
        self._extra_allowed = set(allowed_builtins or [])

    def execute(self, code: str, globals_dict: dict[str, Any]) -> dict[str, Any]:
        """
        在受限命名空间中执行代码
        """
        # 构建安全的 builtins
        safe_builtins = self._build_safe_builtins()

        # 创建命名空间
        namespace = dict(globals_dict)
        namespace["__builtins__"] = safe_builtins
        namespace["__name__"] = "sandbox"
        namespace["__doc__"] = None

        # 执行代码
        exec(code, namespace)

        return namespace

    def _build_safe_builtins(self) -> dict[str, Any]:
        """构建安全的 builtins 字典"""
        # 允许大部分内置函数
        safe = {}
        for name in dir(builtins):
            if name.startswith('_') and name not in ('__import__', '__build_class__'):
                continue
            if name in self.DANGEROUS_FUNCTIONS:
                continue
            safe[name] = getattr(builtins, name)

        # 添加额外允许的
        for name in self._extra_allowed:
            if hasattr(builtins, name):
                safe[name] = getattr(builtins, name)

        return safe


class SubprocessSandbox(Sandbox):
    """
    子进程沙箱（可选实现）

    在独立进程中执行代码，更安全但更慢。
    适用于需要强隔离的场景。
    """

    def __init__(self, timeout: float = 5.0):
        """
        Args:
            timeout: 执行超时时间（秒）
        """
        self.timeout = timeout

    def execute(self, code: str, globals_dict: dict[str, Any]) -> dict[str, Any]:
        """
        在子进程中执行代码
        """
        import subprocess
        import tempfile

        # 写入临时文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_path = f.name

        try:
            # 在子进程中执行
            result = subprocess.run(
                ['python3', temp_path],
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd='/tmp',  # 限制工作目录
            )

            if result.returncode != 0:
                raise RuntimeError(f"Execution failed: {result.stderr}")

            # 返回空的命名空间（子进程无法共享内存）
            return {}

        finally:
            import os
            os.unlink(temp_path)


# 默认沙箱实例
_default_sandbox: Sandbox | None = None


def get_default_sandbox() -> Sandbox:
    """获取默认沙箱实例"""
    global _default_sandbox
    if _default_sandbox is None:
        _default_sandbox = NamespaceSandbox()
    return _default_sandbox


def set_default_sandbox(sandbox: Sandbox) -> None:
    """设置默认沙箱实例"""
    global _default_sandbox
    _default_sandbox = sandbox
