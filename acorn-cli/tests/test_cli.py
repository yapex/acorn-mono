"""
Test for acorn-cli CLI commands
"""
import pytest
from typer.testing import CliRunner
from acorn_cli import app

runner = CliRunner()


def test_cli_help_shows_core_commands():
    """acorn --help 显示核心命令"""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "install" in result.stdout
    assert "list" in result.stdout


def test_cli_list_shows_plugins():
    """acorn list 显示已安装插件"""
    result = runner.invoke(app, ["list"])
    assert result.exit_code == 0
    # 应该显示插件列表（不包含"暂无"）
    assert "已安装插件" in result.stdout


def test_cli_install_command_exists():
    """acorn install 命令存在"""
    result = runner.invoke(app, ["install", "--help"])
    assert result.exit_code == 0


def test_cli_enable_command_exists():
    """acorn config enable 命令存在"""
    result = runner.invoke(app, ["config", "enable", "--help"])
    assert result.exit_code == 0


def test_cli_disable_command_exists():
    """acorn config disable 命令存在"""
    result = runner.invoke(app, ["config", "disable", "--help"])
    assert result.exit_code == 0


def test_cli_config_command_exists():
    """acorn config 命令存在"""
    result = runner.invoke(app, ["config", "--help"])
    assert result.exit_code == 0
