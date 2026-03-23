"""
VI Plugin Extensions
=====================

VI 扩展机制，允许动态加载和注册 VI 扩展。

扩展类型：
- entry_point: 通过 setuptools entry_points 注册的扩展
- local: 本地路径下的扩展

Usage:
    registry = ExtensionRegistry()
    registry.discover()
    for ext in registry.list():
        print(ext.name)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from importlib.metadata import entry_points
from pathlib import Path
from typing import Any


VI_ENTRY_POINT_GROUP = "vi.extensions"


@dataclass
class Extension:
    """VI 扩展"""
    name: str
    entry_point: str = ""
    source: str = "entry_point"  # entry_point, local, git
    path: str = ""

    def load(self) -> Any | None:
        """加载扩展模块"""
        if self.source == "local":
            return self._load_local()
        elif self.source == "entry_point":
            return self._load_entry_point()
        return None

    def _load_local(self) -> Any | None:
        """从本地路径加载"""
        if not self.path:
            return None

        import importlib.util

        init_path = Path(self.path) / "__init__.py"
        if not init_path.exists():
            return None

        spec = importlib.util.spec_from_file_location(self.name, init_path)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return module
        return None

    def _load_entry_point(self) -> Any | None:
        """从 entry point 加载"""
        if not self.entry_point:
            return None

        module_path, _, attr = self.entry_point.partition(":")
        try:
            module = __import__(module_path, fromlist=[attr] if attr else [None])
            return getattr(module, attr) if attr else module
        except (ImportError, AttributeError):
            return None


class ExtensionRegistry:
    """VI 扩展注册表

    管理 VI 扩展的发现和加载。
    """

    def __init__(self) -> None:
        self._extensions: list[Extension] = []
        self._local_paths: list[Path] = []
        self._loaded_modules: dict[str, Any] = {}

    @property
    def ENTRY_POINT_GROUP(self) -> str:
        """Entry point group 名称"""
        return VI_ENTRY_POINT_GROUP

    def discover(self) -> list[Extension]:
        """发现已安装的扩展

        从以下来源发现扩展：
        1. entry_points (通过 setuptools 注册)
        2. 本地路径 (通过 add_local_path 添加)

        Returns:
            发现的扩展列表
        """
        extensions: list[Extension] = []

        # 从 entry_points 发现
        try:
            eps = entry_points(group=self.ENTRY_POINT_GROUP)
            for ep in eps:
                extensions.append(Extension(
                    name=ep.name,
                    entry_point=ep.value,
                    source="entry_point",
                ))
        except Exception:
            # entry_points 可能为空或抛出异常
            pass

        # 添加本地路径扩展
        for path in self._local_paths:
            if path.exists():
                extensions.append(Extension(
                    name=path.name,
                    entry_point="",
                    source="local",
                    path=str(path),
                ))

        self._extensions = extensions
        return extensions

    def list(self) -> list[Extension]:
        """列出所有已发现的扩展"""
        return self._extensions.copy()

    def add_local_path(self, path: str | Path) -> None:
        """添加本地扩展路径

        Args:
            path: 扩展目录路径
        """
        p = Path(path)
        if p.exists() and p.is_dir() and p not in self._local_paths:
            self._local_paths.append(p)

    def get(self, name: str) -> Extension | None:
        """根据名称获取扩展"""
        for ext in self._extensions:
            if ext.name == name:
                return ext
        return None

    def load(self, name: str) -> Any | None:
        """加载扩展模块

        Args:
            name: 扩展名称

        Returns:
            加载的模块对象，如果加载失败返回 None
        """
        # 检查缓存
        if name in self._loaded_modules:
            return self._loaded_modules[name]

        ext = self.get(name)
        if ext is None:
            return None

        module = ext.load()
        if module is not None:
            self._loaded_modules[name] = module
        return module

    def clear(self) -> None:
        """清空注册表和缓存"""
        self._extensions.clear()
        self._loaded_modules.clear()


# 全局默认实例
_default_registry: ExtensionRegistry | None = None


def get_default_registry() -> ExtensionRegistry:
    """获取默认扩展注册表（单例）"""
    global _default_registry
    if _default_registry is None:
        _default_registry = ExtensionRegistry()
    return _default_registry
