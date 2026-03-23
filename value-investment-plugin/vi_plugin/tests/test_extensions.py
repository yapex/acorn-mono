"""
VI Plugin Extensions Tests
==========================
"""

from pathlib import Path

import pytest
from vi_plugin.extensions import ExtensionRegistry, Extension


class TestExtensionRegistry:
    """ExtensionRegistry tests"""

    def test_extension_registry_initializes(self):
        """扩展注册表初始化"""
        registry = ExtensionRegistry()
        assert registry._extensions == []

    def test_discover_finds_entry_points(self):
        """discover 能找到 entry points"""
        registry = ExtensionRegistry()
        extensions = registry.discover()
        assert isinstance(extensions, list)

    def test_extension_dataclass(self):
        """Extension 数据类正常工作"""
        ext = Extension(
            name="test_extension",
            entry_point="test_extension:plugin",
            source="entry_point",
            path="",
        )
        assert ext.name == "test_extension"
        assert ext.entry_point == "test_extension:plugin"
        assert ext.source == "entry_point"

    def test_add_local_path(self):
        """添加本地路径"""
        import tempfile
        registry = ExtensionRegistry()
        with tempfile.TemporaryDirectory() as tmpdir:
            ext_path = Path(tmpdir) / "test-extension"
            ext_path.mkdir()
            registry.add_local_path(ext_path)
            assert len(registry._local_paths) == 1

    def test_add_local_path_prevents_duplicates(self):
        """添加本地路径防止重复"""
        import tempfile
        registry = ExtensionRegistry()
        with tempfile.TemporaryDirectory() as tmpdir:
            ext_path = Path(tmpdir) / "test-extension"
            ext_path.mkdir()
            registry.add_local_path(ext_path)
            registry.add_local_path(ext_path)
            assert len(registry._local_paths) == 1

    def test_discover_includes_local_paths(self):
        """discover 包含本地路径扩展"""
        import tempfile
        from pathlib import Path

        registry = ExtensionRegistry()
        with tempfile.TemporaryDirectory() as tmpdir:
            ext_path = Path(tmpdir) / "test_extension"
            ext_path.mkdir()
            registry.add_local_path(ext_path)

            extensions = registry.discover()
            local_exts = [e for e in extensions if e.source == "local"]
            assert len(local_exts) == 1
            assert local_exts[0].name == "test_extension"
