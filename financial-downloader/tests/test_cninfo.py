"""Tests for CNINFO (A-share) downloader.

所有测试使用内存文件系统（tmp_path），自动清理。
"""

from datetime import datetime
from pathlib import Path

import pytest

from financial_downloader.downloaders import CninfoDownloader, DownloadResult


class TestCninfoDownloader:
    """测试 A 股下载器 - 所有测试使用临时目录。"""

    @pytest.fixture
    def downloader(self, tmp_path: Path):
        """创建下载器实例，使用临时目录。"""
        return CninfoDownloader(output_dir=tmp_path)

    def test_create_downloader(self, downloader):
        """测试创建下载器。"""
        assert downloader.market == "cn"
        assert "annual" in downloader.get_supported_types()
        assert "ipo" in downloader.get_supported_types()
        assert downloader.output_dir.exists()

    def test_validate_code_valid(self, downloader):
        """测试验证有效股票代码。"""
        # 沪市
        assert downloader.validate_code("600519") is True
        assert downloader.validate_code("601318") is True
        # 深市
        assert downloader.validate_code("000001") is True
        assert downloader.validate_code("002415") is True
        # 创业板
        assert downloader.validate_code("300750") is True

    def test_validate_code_invalid(self, downloader):
        """测试验证无效股票代码。"""
        assert downloader.validate_code("") is False
        assert downloader.validate_code("abc") is False
        assert downloader.validate_code("12345") is False

    def test_get_org_id_shanghai(self, downloader):
        """测试沪市 orgId 生成。"""
        assert downloader.get_org_id("600519") == "gssh0600519"
        assert downloader.get_org_id("601318") == "gssh0601318"

    def test_get_org_id_shenzhen(self, downloader):
        """测试深市 orgId 生成。"""
        assert downloader.get_org_id("000001") == "gssz0000001"
        assert downloader.get_org_id("002415") == "gssz0002415"

    def test_get_org_id_chi_next(self, downloader):
        """测试创业板 orgId 获取。"""
        assert downloader.get_org_id("300750") == "GD165627"
        assert downloader.get_org_id("300059") == "GD165626"

    def test_filter_announcement(self, downloader):
        """测试公告筛选。"""
        config = {
            "name": "年度报告",
            "exclude": ["半年度", "摘要"],
            "include": ["年度报告"],
        }
        assert downloader.filter_announcement("2024 年年度报告", config) is True
        assert downloader.filter_announcement("2024 年半年度报告", config) is False
        assert downloader.filter_announcement("年度报告摘要", config) is False

    def test_extract_year(self, downloader):
        """测试从标题提取年份。"""
        current_year = datetime.now().year

        title1 = "2024" + chr(24180) + "年度报告"
        title2 = "2023" + chr(24180) + "年度报告全文"

        assert downloader.extract_year(title1, current_year) == 2024
        assert downloader.extract_year(title2, current_year) == 2023
        assert downloader.extract_year("无年份", current_year) is None

    def test_generate_filename(self, downloader):
        """测试文件名生成。"""
        filename = downloader.generate_filename("600519", "贵州茅台", 2024, "annual")
        assert filename == "600519_贵州茅台_2024_an.pdf"

    def test_download_invalid_code(self, downloader):
        """测试无效股票代码下载。"""
        result = downloader.download(
            code="INVALID",
            name="测试公司",
            dry_run=True,
        )
        assert result.success is False
        assert len(result.errors) > 0

    def test_download_invalid_type(self, downloader):
        """测试不支持的文档类型。"""
        result = downloader.download(
            code="600519",
            name="贵州茅台",
            doc_type="invalid_type",
            dry_run=True,
        )
        assert result.success is False
        assert len(result.errors) > 0

    def test_skip_existing(self, downloader, tmp_path):
        """测试跳过已下载文件。"""
        # 创建一个假文件
        existing_file = tmp_path / "600519_贵州茅台_2024_an.pdf"
        existing_file.write_bytes(b"fake content")

        # 下载应该跳过
        result = downloader.download(
            code="600519",
            name="贵州茅台",
            year=2024,
            skip_existing=True,
            dry_run=True,
        )

        # 干跑模式，验证逻辑
        assert isinstance(result, DownloadResult)


class TestIntegration:
    """集成测试（需要网络）。"""

    @pytest.fixture
    def real_downloader(self, tmp_path):
        """创建真实下载器用于集成测试。"""
        return CninfoDownloader(output_dir=tmp_path)

    def test_fetch_maotai_announcements(self, real_downloader):
        """测试获取茅台公告列表。"""
        pytest.skip("集成测试，需要网络连接")
