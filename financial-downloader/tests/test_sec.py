"""Tests for SEC (US Stock) downloader.

所有测试使用内存文件系统（tmp_path），自动清理。
"""

import pytest
from pathlib import Path
from datetime import datetime
from financial_downloader.downloaders import SecDownloader, DownloadResult


class TestSecDownloader:
    """测试美股下载器 - 所有测试使用临时目录。"""

    @pytest.fixture
    def downloader(self, tmp_path: Path):
        """创建下载器实例，使用临时目录。"""
        return SecDownloader(
            output_dir=tmp_path,
            sec_user_agent="Test Company test@example.com"
        )

    def test_create_downloader(self, downloader):
        """测试创建下载器。"""
        assert downloader.market == "us"
        assert "20-F" in downloader.get_supported_types()
        assert "10-K" in downloader.get_supported_types()
        assert downloader.output_dir.exists()

    def test_validate_code_valid(self, downloader):
        """测试验证有效美股代码。"""
        assert downloader.validate_code("AAPL") is True
        assert downloader.validate_code("TCOM") is True
        assert downloader.validate_code("MSFT") is True
        assert downloader.validate_code("BABA") is True

    def test_validate_code_invalid(self, downloader):
        """测试验证无效美股代码。"""
        assert downloader.validate_code("") is False
        assert downloader.validate_code("123456") is False
        assert downloader.validate_code("a") is False

    def test_validate_cik_valid(self, downloader):
        """测试验证有效 CIK。"""
        assert downloader.validate_cik("0000320193") is True
        assert downloader.validate_cik("0001269238") is True
        assert downloader.validate_cik("320193") is True

    def test_validate_cik_invalid(self, downloader):
        """测试验证无效 CIK。"""
        assert downloader.validate_cik("") is False
        assert downloader.validate_cik("abc") is False
        assert downloader.validate_cik("12345") is False

    def test_get_supported_forms(self, downloader):
        """测试获取支持的表单类型。"""
        forms = downloader.get_supported_forms()
        assert len(forms) > 0
        assert "20-F" in forms or "10-K" in forms

    def test_download_20f_dry_run(self, downloader):
        """测试干跑模式下载 20-F。"""
        result = downloader.download_20f(
            code="TCOM",
            name="Trip.com",
            years=1,
            dry_run=True,
        )
        
        assert isinstance(result, DownloadResult)
        assert result.success is True

    def test_download_10k_dry_run(self, downloader):
        """测试干跑模式下载 10-K。"""
        result = downloader.download_10k(
            code="AAPL",
            name="Apple",
            years=1,
            dry_run=True,
        )
        
        assert isinstance(result, DownloadResult)
        assert result.success is True

    def test_download_invalid_code(self, downloader):
        """测试无效股票代码下载。"""
        result = downloader.download(
            code="INVALID",
            name="测试公司",
            doc_type="20-F",
            dry_run=True,
        )
        
        assert result.success is False
        assert len(result.errors) > 0

    def test_download_invalid_type(self, downloader):
        """测试不支持的文档类型。"""
        result = downloader.download(
            code="AAPL",
            name="Apple",
            doc_type="invalid_type",
            dry_run=True,
        )
        
        assert result.success is False
        assert len(result.errors) > 0

    def test_output_dir_is_tmp_path(self, downloader, tmp_path):
        """验证下载器使用临时目录。"""
        assert downloader.output_dir == tmp_path
        assert "pytest-of" in str(downloader.output_dir)

    def test_sec_user_agent(self, downloader):
        """测试 SEC User-Agent 设置。"""
        assert downloader.sec_user_agent == "Test Company test@example.com"


class TestSecDownloaderWithCIK:
    """测试 CIK 下载。"""

    @pytest.fixture
    def downloader(self, tmp_path: Path):
        """创建下载器实例。"""
        return SecDownloader(
            output_dir=tmp_path,
            sec_user_agent="Test Company test@example.com"
        )

    def test_download_with_cik_dry_run(self, downloader):
        """测试使用 CIK 干跑下载。"""
        result = downloader.download(
            code="0001269238",
            name="Trip.com",
            doc_type="20-F",
            dry_run=True,
        )
        
        assert isinstance(result, DownloadResult)
        assert result.success is True


class TestIntegration:
    """集成测试（需要网络和 sec-edgar-downloader）。"""

    @pytest.fixture
    def real_downloader(self, tmp_path):
        """创建真实下载器用于集成测试。"""
        return SecDownloader(
            output_dir=tmp_path,
            sec_user_agent="Test Company test@example.com"
        )

    def test_download_tencent_20f(self, real_downloader):
        """测试下载携程 20-F。"""
        pytest.skip("集成测试，需要安装 sec-edgar-downloader 和网络连接")

    def test_download_apple_10k(self, real_downloader):
        """测试下载苹果 10-K。"""
        pytest.skip("集成测试，需要安装 sec-edgar-downloader 和网络连接")
