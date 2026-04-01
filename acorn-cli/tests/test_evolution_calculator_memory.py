"""
TDD: Calculator 内存存储测试

测试场景：
- Calculator 支持直接输入字符串的方式添加到内存中
- 通过 evolution.py 的 API 直接在内存中添加 Calculator
"""

import pytest


class TestCalculatorMemoryDirect:
    """
    直接 import evolution 模块测试
    这样可以在同一进程中共享内存
    """

    def test_add_calculator_via_string(self):
        """
        RED: Calculator 应该能通过字符串 code 添加到内存
        
        期望：
        - 调用 apply_calculator(field_name, code)
        - Calculator 被注册到 AVAILABLE_CALCULATORS
        - 后续 check_calculator(field_name) 能找到它
        """
        from acorn_cli.evolution import (
            check_calculator,
            apply_calculator,
            AVAILABLE_CALCULATORS,
        )

        # 记录初始状态
        initial_count = len(AVAILABLE_CALCULATORS)
        field_name = "test_string_calc"

        # 验证初始不存在
        assert check_calculator(field_name) is None

        # 应用计算器
        code = '''REQUIRED_FIELDS = ["field_a", "field_b"]

def calculate(data, config):
    return data["field_a"] / data["field_b"]
'''
        apply_calculator(field_name, code)

        # 验证已注册
        assert field_name in AVAILABLE_CALCULATORS
        assert len(AVAILABLE_CALCULATORS) == initial_count + 1

        # 验证可以查到
        result = check_calculator(field_name)
        assert result is not None
        assert result["description"] == "用户创建"  # apply_calculator 设置的默认描述


class TestCalculatorCLIStringInput:
    """
    测试 CLI 字符串参数输入
    通过 subprocess 调用（进程隔离）
    """

    def test_create_returns_registered_confirmation(self):
        """
        CLI create 操作应该返回 registered 确认信息
        
        这验证了字符串参数能被正确解析和注册
        """
        import subprocess

        result = subprocess.run(
            [
                "python", "-m", "acorn_cli.evolution",
                "--intent", "create",
                "--field-name", "cli_string_test",
                "--formula", "a / b",
                "--required-fields", "a,b",
                "--description", "CLI测试",
                "--unit", "ratio",
                "--code", "REQUIRED_FIELDS = ['a', 'b']\n\ndef calculate(data, config):\n    return data['a'] / data['b']",
                "--confirm",
            ],
            capture_output=True,
            text=True,
            cwd=".",
        )

        output = result.stdout
        # 验证返回 registered 确认
        assert "registered: cli_string_test" in output
        # 验证操作完成
        assert "done" in output


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
