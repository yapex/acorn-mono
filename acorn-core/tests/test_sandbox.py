"""
测试沙箱机制
"""

import pytest


class TestSandboxInterface:
    """测试沙箱接口"""

    def test_can_import_sandbox(self):
        from acorn_core.plugins.sandbox import Sandbox
        assert Sandbox is not None

    def test_sandbox_is_protocol_or_abc(self):
        from acorn_core.plugins.sandbox import Sandbox
        # Sandbox 应该是可以被继承/实现的
        assert hasattr(Sandbox, 'execute')


class TestNamespaceSandbox:
    """测试命名空间沙箱"""

    def test_namespace_sandbox_blocks_dangerous_functions(self):
        from acorn_core.plugins.sandbox import NamespaceSandbox

        sandbox = NamespaceSandbox()

        # open 应该不可用
        assert 'open' not in sandbox._build_safe_builtins()

        # eval 应该不可用
        safe = sandbox._build_safe_builtins()
        assert 'eval' not in safe
        assert 'exec' not in safe
        assert 'compile' not in safe

    def test_namespace_sandbox_allows_safe_code(self):
        from acorn_core.plugins.sandbox import NamespaceSandbox

        sandbox = NamespaceSandbox()

        safe_code = '''
message = "hello"
numbers = [1, 2, 3]
result = len([1, 2, 3])
'''
        namespace = sandbox.execute(safe_code, {})

        assert namespace.get('message') == "hello"
        assert namespace.get('numbers') == [1, 2, 3]
        assert namespace.get('result') == 3

    def test_acorn_can_use_custom_sandbox(self):
        from acorn_core import Acorn
        from acorn_core.plugins.sandbox import Sandbox, NamespaceSandbox

        # 自定义沙箱
        class MockSandbox(Sandbox):
            def execute(self, code: str, globals_dict: dict) -> dict:
                return {"plugin": "mock"}  # 直接返回假的

        mock_sandbox = MockSandbox()
        acorn = Acorn()
        acorn.load_plugins()

        # 调用者使用自定义沙箱执行代码，然后传给 kernel
        namespace = mock_sandbox.execute("any code", {})
        try:
            acorn.install_plugin(namespace)
        except ValueError:
            pass  # 预期 - mock 返回的 namespace 没有 plugin

        # 安装一个真实插件
        real_code = '''
from acorn_core import hookimpl

class TestPlugin:
    @property
    def commands(self):
        return ["test"]

    @hookimpl
    def handle(self, task):
        return {"success": True, "data": "ok"}

    @hookimpl
    def get_capabilities(self):
        return {"commands": ["test"], "args": {}}

plugin = TestPlugin()
'''
        real_sandbox = NamespaceSandbox()
        real_namespace = real_sandbox.execute(real_code, {})
        acorn.install_plugin(real_namespace)

        # 检查插件已加载
        plugins = acorn.list_plugins()
        assert len(plugins) >= 1


class TestSandboxBlocksDangerous:
    """测试沙箱拦截危险操作"""

    def test_blocks_open(self):
        from acorn_core.plugins.sandbox import NamespaceSandbox
        sandbox = NamespaceSandbox()

        code = '''
f = open("/tmp/test.txt", "w")
f.write("test")
'''
        # 应该在执行时报错
        with pytest.raises(NameError):
            sandbox.execute(code, {})

    def test_blocks_eval(self):
        from acorn_core.plugins.sandbox import NamespaceSandbox
        sandbox = NamespaceSandbox()

        code = 'result = eval("1+1")'
        # eval 不可用，应该抛出 NameError
        with pytest.raises(NameError):
            sandbox.execute(code, {})

    def test_blocks_exec(self):
        from acorn_core.plugins.sandbox import NamespaceSandbox
        sandbox = NamespaceSandbox()

        code = 'exec("print(1)")'
        # exec 不可用，应该抛出 NameError
        with pytest.raises(NameError):
            sandbox.execute(code, {})
