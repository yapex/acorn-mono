"""Tests for CLI commands."""


import pytest
import yaml
from typer.testing import CliRunner

from financial_downloader.cli import app

runner = CliRunner()


class TestCliBasic:
    """测试 CLI 基本功能。"""

    def test_cli_help(self):
        """测试 CLI 帮助信息。"""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "fin-down" in result.stdout.lower()

    def test_download_help(self):
        """测试 download 命令帮助。"""
        result = runner.invoke(app, ["download", "--help"])
        assert result.exit_code == 0
        assert "--market" in result.stdout
        assert "--skip-existing" in result.stdout or "-s" in result.stdout

    def test_list_types_help(self):
        """测试 list-types 命令帮助。"""
        result = runner.invoke(app, ["list-types", "--help"])
        assert result.exit_code == 0

    def test_config_command(self):
        """测试 config 命令。"""
        result = runner.invoke(app, ["config"])
        assert result.exit_code == 0


class TestCliDownload:
    """测试 download 命令。"""

    def test_download_requires_market(self):
        """测试 download 命令需要 market 参数。"""
        result = runner.invoke(app, ["download", "600519", "贵州茅台"])
        assert result.exit_code != 0

    def test_download_invalid_market(self):
        """测试无效的 market 参数。"""
        result = runner.invoke(app, [
            "download", "600519", "贵州茅台", "--market", "invalid",
        ])
        assert result.exit_code != 0

    def test_download_dry_run_cn(self):
        """测试 A 股干跑模式。"""
        result = runner.invoke(app, [
            "download", "600519", "贵州茅台", "--market", "cn", "--list",
        ])
        assert result.exit_code == 0

    def test_download_dry_run_hk(self):
        """测试港股干跑模式。"""
        result = runner.invoke(app, [
            "download", "00700", "腾讯控股", "--market", "hk", "--list",
        ])
        assert result.exit_code == 0

    def test_download_dry_run_us(self):
        """测试美股干跑模式。"""
        # 需要 sec-edgar-downloader，跳过
        pytest.skip("需要安装 sec-edgar-downloader")

    def test_download_skip_existing(self):
        """测试跳过已下载选项。"""
        result = runner.invoke(app, [
            "download", "600519", "贵州茅台", "--market", "cn",
            "--skip-existing", "--list",
        ])
        assert result.exit_code == 0


class TestCliListTypes:
    """测试 list-types 命令。"""

    def test_list_types_cn(self):
        """测试列出 A 股文档类型。"""
        result = runner.invoke(app, ["list-types", "-m", "cn"])
        assert result.exit_code == 0
        assert "annual" in result.stdout.lower() or "年报" in result.stdout

    def test_list_types_hk(self):
        """测试列出港股文档类型。"""
        result = runner.invoke(app, ["list-types", "-m", "hk"])
        assert result.exit_code == 0

    def test_list_types_us(self):
        """测试列出美股文档类型。"""
        result = runner.invoke(app, ["list-types", "-m", "us"])
        assert result.exit_code == 0
        assert "20-F" in result.stdout or "10-K" in result.stdout


class TestCliBatch:
    """测试 batch 命令。"""

    def test_batch_help(self):
        """测试 batch 命令帮助。"""
        result = runner.invoke(app, ["batch", "--help"])
        assert result.exit_code == 0

    def test_batch_missing_file(self):
        """测试配置文件不存在。"""
        result = runner.invoke(app, ["batch", "/nonexistent/file.yaml"])
        assert result.exit_code != 0

    def test_batch_empty_config(self, tmp_path):
        """测试空配置文件。"""
        config_file = tmp_path / "empty.yaml"
        config_file.write_text("downloads: []")

        result = runner.invoke(app, ["batch", str(config_file)])
        assert result.exit_code == 0

    def test_batch_valid_config(self, tmp_path):
        """测试有效配置文件（干跑）。"""
        config_file = tmp_path / "test.yaml"
        config = {
            "downloads": [{
                "code": "600519",
                "name": "贵州茅台",
                "market": "cn",
                "years": 1,
                "type": "annual",
            }]
        }
        config_file.write_text(yaml.dump(config))

        result = runner.invoke(app, ["batch", str(config_file), "--list"])
        assert result.exit_code == 0
