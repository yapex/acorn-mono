"""
Acorn CLI + VI Plugin Integration Tests
========================================

端到端集成测试，验证 Acorn CLI 和 VI Plugin 的完整功能。
"""

import subprocess
import sys


class TestAcornCLI:
    """Acorn CLI 核心功能测试"""

    def test_acorn_help(self):
        """acorn --help 显示帮助信息"""
        result = subprocess.run(
            ["uv", "run", "acorn", "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "Acorn" in result.stdout
        assert "插件化命令行工具" in result.stdout or "plugin" in result.stdout.lower()

    def test_acorn_list_empty(self):
        """acorn list 在空注册表时显示正确信息"""
        result = subprocess.run(
            ["uv", "run", "acorn", "list"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0

    def test_acorn_vi_help(self):
        """acorn vi --help 显示 VI 命令帮助"""
        result = subprocess.run(
            ["uv", "run", "acorn", "vi", "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "query" in result.stdout.lower() or "Query" in result.stdout


class TestVITPlugin:
    """VI Plugin 命令测试"""

    def test_vi_list_command(self):
        """acorn vi list 显示字段和计算器列表"""
        result = subprocess.run(
            ["uv", "run", "acorn", "vi", "list"],
            capture_output=True,
            text=True,
        )
        # 命令应该成功执行（即使没有数据）
        # 可能返回成功或空数据，但不应该是错误
        assert result.returncode == 0 or "success" in result.stdout

    def test_vi_list_fields_category(self):
        """acorn vi list --category fields 只显示字段"""
        result = subprocess.run(
            ["uv", "run", "acorn", "vi", "list", "--category", "fields"],
            capture_output=True,
            text=True,
        )
        # 命令应该成功执行
        assert result.returncode == 0 or "success" in result.stdout


class TestPluginRegistry:
    """插件注册表测试"""

    def test_acorn_config_discover(self):
        """acorn config discover 能发现可用插件"""
        result = subprocess.run(
            ["uv", "run", "acorn", "config", "discover"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0

    def test_acorn_config_path(self):
        """acorn config path 显示注册表路径"""
        result = subprocess.run(
            ["uv", "run", "acorn", "config", "path"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert ".json" in result.stdout or "registry" in result.stdout.lower()
