"""
任务上下文 (Task Context)
"""
from __future__ import annotations

from typing import Any


class TaskContext:
    """
    任务执行上下文

    Attributes:
        task: 原始任务描述
        capabilities: 发现的可用能力列表
        results: 任务执行结果
        state: 自由状态字典
    """

    def __init__(self, task: str) -> None:
        self.task: str = task
        self.capabilities: list[dict[str, Any]] = []
        self.results: list[Any] = []
        self.state: dict[str, Any] = {}

    def add_capability(self, capability: dict[str, Any]) -> None:
        """添加一个能力"""
        if capability:
            self.capabilities.append(capability)

    def add_result(self, result: Any) -> None:
        """添加一个执行结果"""
        self.results.append(result)

    def __repr__(self) -> str:
        cap = len(self.capabilities)
        res = len(self.results)
        return f"TaskContext(task={self.task!r}, caps={cap}, res={res})"
