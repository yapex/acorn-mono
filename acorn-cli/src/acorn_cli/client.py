"""
HTTP Client for acorn-agent
"""
from __future__ import annotations

from typing import Any

import httpx

# 默认地址
DEFAULT_BASE_URL = "http://127.0.0.1:18732"


class AcornClient:
    """HTTP Client for Acorn Agent"""

    def __init__(self, base_url: str = DEFAULT_BASE_URL) -> None:
        self.base_url = base_url
        self._client = httpx.Client(timeout=30.0)

    def health_check(self) -> dict[str, Any]:
        """健康检查"""
        response = self._client.get(f"{self.base_url}/health")
        response.raise_for_status()
        return response.json()

    def status(self) -> dict[str, Any]:
        """获取系统状态"""
        response = self._client.get(f"{self.base_url}/status")
        response.raise_for_status()
        return response.json()

    def execute(self, command: str, args: dict[str, Any] | None = None) -> dict[str, Any]:
        """执行命令"""
        if args is None:
            args = {}
        response = self._client.post(
            f"{self.base_url}/execute",
            json={"command": command, "args": args},
        )
        response.raise_for_status()
        return response.json()

    def list_commands(self) -> dict[str, Any]:
        """列出可用命令"""
        response = self._client.get(f"{self.base_url}/commands")
        response.raise_for_status()
        return response.json()

    def __call__(self, command: str, **kwargs: Any) -> dict[str, Any]:
        """快捷调用: client("status")"""
        return self.execute(command, kwargs)

    def close(self) -> None:
        """关闭客户端"""
        self._client.close()

    def __enter__(self) -> "AcornClient":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()
