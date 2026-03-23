"""
Tests for TUI module
"""
import pytest
from acorn_cli.tui import format_plugin_entry
from acorn_cli.registry import PluginEntry


def test_format_plugin_entry_enabled():
    """格式化的插件条目显示启用状态"""
    entry = PluginEntry(
        name="echo",
        entry_point="echo:plugin",
        version="1.0.0",
        enabled=True,
        source="pypi",
    )
    result = format_plugin_entry(entry)
    assert "✓" in result
    assert "echo" in result
    assert "1.0.0" in result


def test_format_plugin_entry_disabled():
    """格式化的插件条目显示禁用状态"""
    entry = PluginEntry(
        name="test",
        entry_point="test:plugin",
        version="2.0.0",
        enabled=False,
    )
    result = format_plugin_entry(entry)
    assert "✗" in result
    assert "test" in result


def test_format_plugin_entry_local_source():
    """格式化本地插件显示正确图标"""
    entry = PluginEntry(
        name="local_plugin",
        entry_point="local:p",
        version="1.0.0",
        enabled=True,
        source="local",
    )
    result = format_plugin_entry(entry)
    assert "📁" in result


def test_format_plugin_entry_unknown_version():
    """格式化版本未知插件"""
    entry = PluginEntry(
        name="test",
        entry_point="test:p",
        version="unknown",
        enabled=True,
    )
    result = format_plugin_entry(entry)
    assert "unknown" not in result  # 不应该显示 "unknown"


def test_format_plugin_entry_long_name():
    """格式化长名称插件被截断"""
    entry = PluginEntry(
        name="this_is_a_very_long_plugin_name_that_should_be_truncated",
        entry_point="test:p",
        version="1.0.0",
        enabled=True,
    )
    result = format_plugin_entry(entry)
    # 名称应该被截断到20字符
    assert len(result) <= 50  # 简化检查
