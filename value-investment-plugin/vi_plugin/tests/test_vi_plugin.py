"""
Tests for VI Plugin
"""
import pytest
from vi_plugin import plugin


def test_vi_plugin_exports_correct_commands():
    """VI 插件导出正确的命令"""
    assert hasattr(plugin, "commands")
    commands = plugin.commands if callable(plugin.commands) else plugin.commands
    assert "vi_query" in commands
    assert "vi_list_fields" in commands
    assert "vi_list_calculators" in commands


def test_vi_plugin_handles_query_command():
    """VI 插件能处理查询命令"""
    from acorn_core import Task

    task = Task(command="vi_query", args={"symbol": "600519"})
    result = plugin.handle(task)

    assert isinstance(result, dict)
    assert "success" in result


def test_vi_plugin_handles_list_fields():
    """VI 插件能处理 list_fields 命令"""
    from acorn_core import Task

    task = Task(command="vi_list_fields", args={})
    result = plugin.handle(task)

    assert isinstance(result, dict)
    assert result.get("success") is True


def test_vi_plugin_handles_list_calculators():
    """VI 插件能处理 list_calculators 命令"""
    from acorn_core import Task

    task = Task(command="vi_list_calculators", args={})
    result = plugin.handle(task)

    assert isinstance(result, dict)
    assert result.get("success") is True


def test_vi_plugin_rejects_unknown_command():
    """VI 插件拒绝未知命令"""
    from acorn_core import Task

    task = Task(command="unknown_command", args={})
    result = plugin.handle(task)

    assert isinstance(result, dict)
    assert result.get("success") is False
    assert result.get("error", {}).get("code") == "NOT_IMPLEMENTED"
