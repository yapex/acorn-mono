"""
测试新的结构化 API
"""

import pytest


class TestTaskResponse:
    """测试 Task 和 Response 类型"""

    def test_can_import_task_and_response(self):
        from acorn_core import Task, Response
        assert Task is not None
        assert Response is not None

    def test_task_has_required_fields(self):
        from acorn_core import Task
        task = Task(command="echo", args={"message": "hello"})
        assert task.command == "echo"
        assert task.args == {"message": "hello"}
        assert task.context == {}
        assert task.options == {}

    def test_response_success(self):
        from acorn_core import Response
        resp = Response(success=True, data="hello")
        assert resp.success is True
        assert resp.data == "hello"
        assert resp.error is None

    def test_response_error(self):
        from acorn_core import Response, ErrorInfo
        resp = Response(
            success=False,
            error=ErrorInfo(code="NOT_IMPLEMENTED", message="No plugin handles this")
        )
        assert resp.success is False
        assert resp.error is not None
        assert resp.error.code == "NOT_IMPLEMENTED"


class TestExecute:
    """测试 execute 方法"""

    def test_execute_returns_response(self):
        from acorn_core import Acorn, Task
        acorn = Acorn()
        acorn.load_plugins()
        
        task = Task(command="echo", args={"message": "hello"})
        result = acorn.execute(task)
        
        assert hasattr(result, "success")
        assert hasattr(result, "data")
        assert hasattr(result, "error")

    def test_execute_unknown_command_returns_error(self):
        from acorn_core import Acorn, Task
        acorn = Acorn()
        acorn.load_plugins()
        
        task = Task(command="unknown_command_xyz", args={})
        result = acorn.execute(task)
        
        assert result.success is False
        assert result.error is not None
        assert result.error.code == "NOT_IMPLEMENTED"

    def test_execute_with_valid_command(self):
        from acorn_core import Acorn, Task, hookimpl
        from acorn_core.plugins.sandbox import NamespaceSandbox
        
        acorn = Acorn()
        acorn.load_plugins()
        
        # 动态安装测试插件
        code = '''
from acorn_core import hookimpl

class TestPlugin:
    commands = ["test_cmd"]
    
    @hookimpl
    def handle(self, task):
        return {"success": True, "data": f"test: {task.args.get('value', '')}"}
    
    @hookimpl
    def get_capabilities(self):
        return {
            "commands": ["test_cmd"],
            "args": {"value": {"type": "string", "required": True}}
        }

plugin = TestPlugin()
'''
        # 调用者负责执行代码（使用沙箱）
        sandbox = NamespaceSandbox()
        namespace = sandbox.execute(code, {})
        
        # 传入执行后的 namespace
        acorn.install_plugin(namespace)
        
        task = Task(command="test_cmd", args={"value": "hello"})
        result = acorn.execute(task)
        
        assert result.success is True
        assert result.data == "test: hello"


class TestExecuteBatch:
    """测试批量执行"""

    def test_execute_batch(self):
        from acorn_core import Acorn, Task
        acorn = Acorn()
        acorn.load_plugins()
        
        tasks = [
            Task(command="echo", args={"message": "hello"}),
            Task(command="unknown", args={}),
        ]
        results = acorn.execute_batch(tasks)
        
        assert len(results) == 2
        assert results[0].success is True   # echo 插件存在
        assert results[0].data == "hello"
        assert results[1].success is False  # unknown 命令不存在


class TestListCapabilities:
    """测试能力清单"""

    def test_list_capabilities_returns_structure(self):
        from acorn_core import Acorn
        acorn = Acorn()
        acorn.load_plugins()
        
        caps = acorn.list_capabilities()
        assert isinstance(caps, list)
        # EvoManager 应该声明能力
        assert len(caps) > 0

    def test_capabilities_have_commands(self):
        from acorn_core import Acorn
        acorn = Acorn()
        acorn.load_plugins()
        
        caps = acorn.list_capabilities()
        # 至少有一个能力声明了 commands
        assert any("commands" in c for c in caps)


class TestErrorCodes:
    """测试错误码"""

    def test_not_implemented_error_code(self):
        from acorn_core import Acorn, Task, ErrorInfo
        acorn = Acorn()
        acorn.load_plugins()
        
        task = Task(command="this_does_not_exist", args={})
        result = acorn.execute(task)
        
        assert result.success is False
        assert result.error is not None
        assert result.error.code == ErrorInfo.NOT_IMPLEMENTED

    def test_invalid_argument_error_code(self):
        from acorn_core import Acorn, Task, ErrorInfo, hookimpl
        from acorn_core.plugins.sandbox import NamespaceSandbox
        
        acorn = Acorn()
        acorn.load_plugins()
        
        # 安装一个强制要求参数的插件
        code = '''
from acorn_core import hookimpl

class StrictPlugin:
    commands = ["strict"]
    
    @hookimpl
    def handle(self, task):
        if "required_arg" not in task.args:
            return {"success": False, "error": "INVALID_ARGUMENT: required_arg is missing"}
        return {"success": True, "data": "ok"}
    
    @hookimpl
    def get_capabilities(self):
        return {
            "commands": ["strict"],
            "args": {"required_arg": {"type": "string", "required": True}}
        }

plugin = StrictPlugin()
'''
        # 调用者负责执行代码（使用沙箱）
        sandbox = NamespaceSandbox()
        namespace = sandbox.execute(code, {})
        acorn.install_plugin(namespace)
        
        # 不带必需参数
        task = Task(command="strict", args={})
        result = acorn.execute(task)
        
        assert result.success is False
        assert result.error is not None
        assert result.error.code == ErrorInfo.INVALID_ARGUMENT
