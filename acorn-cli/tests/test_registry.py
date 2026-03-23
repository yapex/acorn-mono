"""
Tests for PluginRegistry
"""
import pytest
import tempfile
from pathlib import Path
from acorn_cli.registry import PluginRegistry, PluginEntry


def test_registry_creates_file_on_first_save():
    """注册表在首次保存时创建文件"""
    with tempfile.TemporaryDirectory() as tmpdir:
        registry_path = Path(tmpdir) / "registry.json"
        registry = PluginRegistry(path=registry_path)

        # 注册一个插件
        entry = PluginEntry(
            name="test_plugin",
            entry_point="test_plugin:plugin",
            version="1.0.0",
        )
        registry._plugins["test_plugin"] = entry
        registry._save()

        assert registry_path.exists()


def test_registry_loads_saved_plugins():
    """注册表能加载已保存的插件"""
    with tempfile.TemporaryDirectory() as tmpdir:
        registry_path = Path(tmpdir) / "registry.json"

        # 创建并保存
        registry1 = PluginRegistry(path=registry_path)
        entry = PluginEntry(name="test", entry_point="test:plugin")
        registry1._plugins["test"] = entry
        registry1._save()

        # 重新加载
        registry2 = PluginRegistry(path=registry_path)
        assert "test" in registry2._plugins


def test_registry_install_plugin():
    """注册表能安装插件（模拟）"""
    registry = PluginRegistry(path=":memory:")

    # 注意：实际安装需要 uv，这里测试注册逻辑
    entry = PluginEntry(
        name="echo",
        entry_point="examples_plugin.echo:plugin",
        version="0.1.0",
        source="local",
    )
    registry._plugins["echo"] = entry
    registry._save()

    assert registry.get("echo") is not None
    assert registry.get("echo").enabled is True


def test_registry_enable_disable():
    """注册表能启用/禁用插件"""
    registry = PluginRegistry(path=":memory:")
    entry = PluginEntry(name="test", entry_point="test:plugin")
    registry._plugins["test"] = entry

    registry.disable("test")
    assert registry.get("test").enabled is False

    registry.enable("test")
    assert registry.get("test").enabled is True


def test_registry_toggle():
    """注册表能切换插件状态"""
    registry = PluginRegistry(path=":memory:")
    entry = PluginEntry(name="test", entry_point="test:plugin", enabled=True)
    registry._plugins["test"] = entry

    registry.toggle("test")
    assert registry.get("test").enabled is False

    registry.toggle("test")
    assert registry.get("test").enabled is True


def test_registry_get_enabled():
    """注册表能获取所有启用的插件"""
    registry = PluginRegistry(path=":memory:")
    registry._plugins["enabled1"] = PluginEntry(name="enabled1", entry_point="e1:p", enabled=True)
    registry._plugins["enabled2"] = PluginEntry(name="enabled2", entry_point="e2:p", enabled=True)
    registry._plugins["disabled"] = PluginEntry(name="disabled", entry_point="d:p", enabled=False)

    enabled = registry.get_enabled()
    assert len(enabled) == 2
    assert all(e.enabled for e in enabled)


def test_registry_update_status():
    """注册表能批量更新状态"""
    registry = PluginRegistry(path=":memory:")
    registry._plugins["a"] = PluginEntry(name="a", entry_point="a:p", enabled=True)
    registry._plugins["b"] = PluginEntry(name="b", entry_point="b:p", enabled=True)

    # 不变更任何状态
    count = registry.update_status({"a": True, "b": True})
    assert count == 0

    # 变更一个
    count = registry.update_status({"a": False, "b": True})
    assert count == 1
    assert registry.get("a").enabled is False


def test_plugin_entry_to_dict_from_dict():
    """PluginEntry 能正确序列化/反序列化"""
    entry = PluginEntry(
        name="test",
        entry_point="test:p",
        version="1.0.0",
        enabled=True,
        source="pypi",
    )

    data = entry.to_dict()
    restored = PluginEntry.from_dict(data)

    assert restored.name == entry.name
    assert restored.entry_point == entry.entry_point
    assert restored.version == entry.version
    assert restored.enabled == entry.enabled
    assert restored.source == entry.source


def test_registry_enable_disable_persistence():
    """测试启用/禁用状态能够正确保存到文件"""
    with tempfile.TemporaryDirectory() as tmpdir:
        registry_path = Path(tmpdir) / "registry.json"

        # 创建第一个 registry 实例并添加插件
        registry1 = PluginRegistry(path=registry_path)
        entry = PluginEntry(name="test", entry_point="test:plugin", enabled=True)
        registry1._plugins["test"] = entry
        registry1._save()

        # 禁用插件
        registry1.disable("test")
        assert registry1.get("test").enabled is False

        # 创建新的 registry 实例（模拟重新加载）
        registry2 = PluginRegistry(path=registry_path)
        assert registry2.get("test").enabled is False, "禁用状态应该被持久化"

        # 启用插件
        registry2.enable("test")
        assert registry2.get("test").enabled is True

        # 再次创建新的 registry 实例
        registry3 = PluginRegistry(path=registry_path)
        assert registry3.get("test").enabled is True, "启用状态应该被持久化"


def test_registry_file_not_corrupted():
    """测试文件不会被损坏（没有多余字符）"""
    with tempfile.TemporaryDirectory() as tmpdir:
        registry_path = Path(tmpdir) / "registry.json"
        registry = PluginRegistry(path=registry_path)

        # 添加多个插件
        for i in range(3):
            entry = PluginEntry(name=f"plugin{i}", entry_point=f"p{i}:plugin")
            registry._plugins[f"plugin{i}"] = entry

        # 多次保存和加载
        for _ in range(5):
            registry.toggle("plugin0")
            registry._save()

            # 验证文件可以正确解析
            with open(registry_path) as f:
                import json
                data = json.load(f)  # 如果文件损坏会抛出异常
                assert "plugins" in data
                assert len(data["plugins"]) == 3
