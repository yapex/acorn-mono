"""
类型定义
========
结构化 API 的核心类型。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Task:
    """
    任务请求

    Attributes:
        command: 命令名 (snake_case)
        args: 参数字典
        context: 上下文信息
        options: 执行选项 (stream, batch, timeout...)
    """
    command: str
    args: dict[str, Any] = field(default_factory=dict)
    context: dict[str, Any] = field(default_factory=dict)
    options: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.command:
            raise ValueError("command cannot be empty")


@dataclass
class ErrorInfo:
    """
    错误信息

    错误码:
        NOT_IMPLEMENTED - 没有插件能处理此命令
        INVALID_ARGUMENT - 参数格式错误
        PLUGIN_ERROR - 插件执行时出错
        TIMEOUT - 执行超时
        INTERNAL - 内部错误
    """
    code: str
    message: str
    detail: str | None = None

    # 错误码常量
    NOT_IMPLEMENTED = "NOT_IMPLEMENTED"
    INVALID_ARGUMENT = "INVALID_ARGUMENT"
    PLUGIN_ERROR = "PLUGIN_ERROR"
    TIMEOUT = "TIMEOUT"
    INTERNAL = "INTERNAL"


@dataclass
class Response:
    """
    执行结果

    Attributes:
        success: 是否成功
        data: 返回数据
        error: 错误信息 (失败时有值)
        meta: 元信息 (来源插件、执行时间等)
    """
    success: bool
    data: Any = None
    error: ErrorInfo | None = None
    meta: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def ok(cls, data: Any = None, meta: dict | None = None) -> Response:
        """创建成功响应"""
        return cls(success=True, data=data, meta=meta or {})

    @classmethod
    def err(cls, code: str, message: str, detail: str | None = None) -> Response:
        """创建错误响应"""
        return cls(
            success=False,
            error=ErrorInfo(code=code, message=message, detail=detail)
        )


@dataclass
class Capabilities:
    """
    能力声明

    Attributes:
        commands: 支持的命令列表
        args: 参数规范
    """
    commands: list[str]
    args: dict[str, dict] = field(default_factory=dict)
