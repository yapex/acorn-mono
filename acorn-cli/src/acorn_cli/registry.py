"""
插件注册表 (Plugin Registry)
============================
持久化管理已安装插件的配置。

注册表文件: .acorn/registry.json
"""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any
from datetime import datetime


@dataclass
class PluginEntry:
    """插件条目"""
    name: str                          # 插件名称 (唯一标识)
    entry_point: str                   # 入口点 "module:variable"
    version: str = "unknown"           # 版本号
    enabled: bool = True               # 是否启用
    source: str = "pypi"               # 来源: pypi, local, git
    source_path: str = ""              # 本地路径或 git URL
    installed_at: str = ""             # 安装时间
    description: str = ""              # 描述

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PluginEntry:
        return cls(**data)


class PluginRegistry:
    """
    插件注册表

    存储位置优先级:
    1. ACORN_REGISTRY_PATH 环境变量
    2. 当前目录 .acorn/registry.json
    3. 用户目录 ~/.acorn/registry.json
    """

    DEFAULT_REGISTRY_NAME = "registry.json"

    def __init__(self, path: Path | str | None = None) -> None:
        self._in_memory = path == ":memory:" or str(path) == ":memory:"
        self.path = self._resolve_path(path)
        self._plugins: dict[str, PluginEntry] = {}
        if not self._in_memory:
            self._load()

    def _resolve_path(self, path: Path | str | None) -> Path:
        """解析注册表路径"""
        import os

        # 1. 显式指定路径
        if path:
            return Path(path)

        # 2. 环境变量
        env_path = os.environ.get("ACORN_REGISTRY_PATH")
        if env_path:
            return Path(env_path)

        # 3. 当前目录 .acorn/
        local_path = Path.cwd() / ".acorn" / self.DEFAULT_REGISTRY_NAME
        if local_path.parent.exists():
            return local_path

        # 4. 用户目录 ~/.acorn/
        return Path.home() / ".acorn" / self.DEFAULT_REGISTRY_NAME

    def _load(self) -> None:
        """加载注册表"""
        if not self.path.exists():
            self._plugins = {}
            return

        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)

            self._plugins = {
                name: PluginEntry.from_dict(entry)
                for name, entry in data.get("plugins", {}).items()
            }
        except (json.JSONDecodeError, KeyError):
            self._plugins = {}

    def _save(self) -> None:
        """保存注册表"""
        self.path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "version": "1.0",
            "updated_at": datetime.now().isoformat(),
            "plugins": {
                name: entry.to_dict()
                for name, entry in self._plugins.items()
            }
        }

        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _run_uv(self, args: list[str]) -> tuple[bool, str]:
        """执行 uv 命令"""
        try:
            result = subprocess.run(
                ["uv", *args],
                capture_output=True,
                text=True,
                timeout=120
            )
            if result.returncode == 0:
                return True, result.stdout
            return False, result.stderr or result.stdout
        except subprocess.TimeoutExpired:
            return False, "Timeout: installation took too long"
        except FileNotFoundError:
            return False, "uv not found. Please install uv first."

    def _get_package_version(self, package_name: str) -> str:
        """获取已安装包的版本"""
        try:
            result = subprocess.run(
                ["uv", "pip", "show", package_name],
                capture_output=True,
                text=True
            )
            for line in result.stdout.split("\n"):
                if line.startswith("Version:"):
                    return line.split(":", 1)[1].strip()
        except Exception:
            pass
        return "unknown"

    def _discover_entry_point(self, package_name: str) -> str | None:
        """自动发现包的 acorn 插件入口点"""
        try:
            from importlib.metadata import entry_points

            eps = entry_points(group="yapex.acorn.plugins")
            for ep in eps:
                # 尝试匹配包名
                if package_name.replace("-", "_") in ep.value.replace("-", "_"):
                    return f"{ep.value}"
        except Exception:
            pass
        return None

    def install(
        self,
        source: str,
        name: str | None = None,
        entry_point: str | None = None,
    ) -> tuple[bool, str]:
        """
        注册插件到 registry

        注意：此命令只记录插件信息，不执行实际安装。
        实际安装请使用 uv 命令：
          - 本地开发: uv pip install -e <path>
          - 生产环境: uv tool install acorn-cli --with-editable <path>

        Args:
            source: 插件来源 (包名/本地路径/git URL)
            name: 插件名称 (可选，默认从 source 推断)
            entry_point: 入口点 (可选，默认自动发现)

        Returns:
            (success, message)
        """
        # 判断来源类型
        source_path = Path(source)
        if source.startswith(("http://", "https://", "git@", "git+")):
            source_type = "git"
            package_name = source.split("/")[-1].replace(".git", "")
        elif source_path.exists():
            source_type = "local"
            package_name = source_path.name
        else:
            source_type = "pypi"
            package_name = source

        # 推断或使用提供的名称
        plugin_name = name or package_name.replace("-", "_").replace(" ", "_")

        # 自动发现或使用提供的入口点
        if not entry_point:
            entry_point = self._discover_entry_point(package_name)
            if not entry_point:
                # 尝试默认格式
                module_name = package_name.replace("-", "_")
                entry_point = f"{module_name}:plugin"

        # 注册到注册表
        entry = PluginEntry(
            name=plugin_name,
            entry_point=entry_point,
            version=version,
            enabled=True,
            source=source_type,
            source_path=str(source_path) if source_type == "local" else source,
            installed_at=datetime.now().isoformat(),
        )

        self._plugins[plugin_name] = entry
        self._save()

        return True, f"Plugin '{plugin_name}' installed successfully"

    def uninstall(self, name: str) -> tuple[bool, str]:
        """
        卸载插件

        Args:
            name: 插件名称

        Returns:
            (success, message)
        """
        if name not in self._plugins:
            return False, f"Plugin '{name}' not found in registry"

        entry = self._plugins[name]

        # 从注册表移除
        del self._plugins[name]
        self._save()

        # 可选: 卸载包 (对于 local 类型不卸载)
        if entry.source != "local":
            # 推断包名
            package_name = entry.name.replace("_", "-")
            self._run_uv(["pip", "uninstall", "-y", package_name])

        return True, f"Plugin '{name}' uninstalled"

    def enable(self, name: str) -> tuple[bool, str]:
        """启用插件"""
        if name not in self._plugins:
            return False, f"Plugin '{name}' not found"

        self._plugins[name].enabled = True
        self._save()
        return True, f"Plugin '{name}' enabled"

    def disable(self, name: str) -> tuple[bool, str]:
        """禁用插件"""
        if name not in self._plugins:
            return False, f"Plugin '{name}' not found"

        self._plugins[name].enabled = False
        self._save()
        return True, f"Plugin '{name}' disabled"

    def toggle(self, name: str) -> tuple[bool, str]:
        """切换插件状态"""
        if name not in self._plugins:
            return False, f"Plugin '{name}' not found"

        entry = self._plugins[name]
        entry.enabled = not entry.enabled
        self._save()

        status = "enabled" if entry.enabled else "disabled"
        return True, f"Plugin '{name}' {status}"

    def list(self) -> list[PluginEntry]:
        """列出所有已注册插件"""
        return list(self._plugins.values())

    def get_enabled(self) -> list[PluginEntry]:
        """获取所有启用的插件"""
        return [e for e in self._plugins.values() if e.enabled]

    def get(self, name: str) -> PluginEntry | None:
        """获取单个插件"""
        return self._plugins.get(name)

    def update_status(self, statuses: dict[str, bool]) -> int:
        """
        批量更新插件状态

        Args:
            statuses: {plugin_name: enabled}

        Returns:
            更新的数量
        """
        count = 0
        for name, enabled in statuses.items():
            if name in self._plugins and self._plugins[name].enabled != enabled:
                self._plugins[name].enabled = enabled
                count += 1

        if count > 0:
            self._save()

        return count

    def discover_available(self) -> list[dict[str, Any]]:
        """
        发现所有可用的 acorn 插件 (已安装但未注册的)

        Returns:
            可用插件列表
        """
        from importlib.metadata import entry_points

        available = []
        registered_names = set(self._plugins.keys())

        try:
            eps = entry_points(group="yapex.acorn.plugins")
            for ep in eps:
                if ep.name not in registered_names:
                    available.append({
                        "name": ep.name,
                        "entry_point": ep.value,
                        "registered": False,
                    })
        except Exception:
            pass

        return available

    @property
    def path_str(self) -> str:
        """返回注册表路径字符串"""
        return str(self.path)
