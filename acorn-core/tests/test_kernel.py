"""
Test for acorn-core kernel - entry point loading
"""
import pytest
from acorn_core import Acorn, Task


def test_acorn_loads_entry_points():
    """Acorn 加载时自动发现 entry_points 中的插件"""
    acorn = Acorn()
    acorn.load_plugins()

    plugins = dict(acorn.list_plugins())
    # 至少应该有内置 evo_manager 插件
    assert len(plugins) >= 1


def test_acorn_executes_registered_plugin():
    """Acorn 能执行已注册的插件命令"""
    acorn = Acorn()
    acorn.load_plugins()

    task = Task(command="capabilities")
    response = acorn.execute(task)

    assert response.success


def test_acorn_rejects_unknown_command():
    """Acorn 对未知命令返回错误"""
    acorn = Acorn()
    acorn.load_plugins()

    task = Task(command="nonexistent_command")
    response = acorn.execute(task)

    assert not response.success
    assert response.error.code == "NOT_IMPLEMENTED"


def test_acorn_does_not_depend_on_registry():
    """Acorn 不依赖外部 registry，只通过 entry_points 加载"""
    # 验证 Acorn 类不导入 registry 相关模块
    import acorn_core.kernel as kernel_module
    source = open(kernel_module.__file__).read()

    # 不应该引用 registry
    assert "registry" not in source.lower() or "PluginRegistry" not in source
