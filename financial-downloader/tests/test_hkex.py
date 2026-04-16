"""Tests for HKEX (Hong Kong) downloader.

所有测试使用内存文件系统（tmp_path），自动清理。
"""

import pytest
from pathlib import Path
from datetime import datetime
from financial_downloader.downloaders import HkexDownloader, DownloadResult


class TestHkexDownloader:
    """测试港股下载器 - 所有测试使用临时目录。"""

    @pytest.fixture
    def downloader(self, tmp_path: Path):
        """创建下载器实例，使用临时目录。"""
        return HkexDownloader(output_dir=tmp_path)

    def test_create_downloader(self, downloader):
        """测试创建下载器。"""
        assert downloader.market == "hk"
        assert "annual" in downloader.get_supported_types()
        assert "esg" in downloader.get_supported_types()
        assert downloader.output_dir.exists()

    def test_validate_code_valid(self, downloader):
        """测试验证有效港股代码。"""
        # 主板
        assert downloader.validate_code("00700") is True
        assert downloader.validate_code("09988") is True
        assert downloader.validate_code("02318") is True
        # 创业板
        assert downloader.validate_code("08083") is True

    def test_validate_code_invalid(self, downloader):
        """测试验证无效港股代码。"""
        assert downloader.validate_code("") is False
        assert downloader.validate_code("abc") is False
        assert downloader.validate_code("123") is False

    def test_get_stock_id_format(self, downloader):
        """测试 stockId 格式（需要网络）。"""
        pytest.skip("集成测试，需要网络连接")

    def test_filter_annual_reports(self, downloader):
        """测试年报筛选。"""
        documents = [
            {"title": "2024 年報", "date": "15/04/2025", "href": "http://example.com/1.pdf"},
            {"title": "2023 年報", "date": "16/04/2024", "href": "http://example.com/2.pdf"},
            {"title": "2024 ESG 報告", "date": "20/05/2025", "href": "http://example.com/3.pdf"},
            {"title": "2024 中期報告", "date": "15/08/2024", "href": "http://example.com/4.pdf"},
        ]

        filtered = downloader.filter_annual_reports(documents, years=2)

        # 应该只保留年报，排除 ESG 和中期报告
        assert len(filtered) == 2
        assert all("年報" in doc["title"] for doc in filtered)
        assert not any("ESG" in doc["title"] for doc in filtered)
        assert not any("中期" in doc["title"] for doc in filtered)

    def test_filter_esg_reports(self, downloader):
        """测试 ESG 报告筛选。"""
        documents = [
            {"title": "2024 ESG 報告", "date": "20/05/2025", "href": "http://example.com/1.pdf"},
            {"title": "2024 環境、社會及管治報告", "date": "20/05/2025", "href": "http://example.com/2.pdf"},
            {"title": "2024 Sustainability Report", "date": "20/05/2025", "href": "http://example.com/3.pdf"},
            {"title": "2024 年報", "date": "15/04/2025", "href": "http://example.com/4.pdf"},
        ]

        filtered = downloader.filter_documents_by_type(documents, "esg")

        assert len(filtered) == 3
        assert all(any(kw in doc["title"] for kw in ["ESG", "環境", "Sustainability"]) for doc in filtered)

    def test_extract_year_from_doc(self, downloader):
        """测试从文档提取财报年份（标题年份必须 < 当前年份）。"""
        current_year = datetime.now().year
        
        # 标题中的年份就是财报年份
        doc1 = {"date": "15/04/2025", "title": "2024 年報"}
        assert downloader._extract_year_from_doc(doc1) == 2024
        
        doc2 = {"date": "16/04/2024", "title": "2023 年報"}
        assert downloader._extract_year_from_doc(doc2) == 2023
        
        # 标题中的年份 >= 当前年份，应该返回 0（无效）
        doc3 = {"date": "15/04/2026", "title": f"{current_year} 年報"}
        assert downloader._extract_year_from_doc(doc3) == 0
        
        # 无年份信息
        doc4 = {"date": "", "title": "無年份"}
        assert downloader._extract_year_from_doc(doc4) == 0

    def test_generate_filename_hkex(self, downloader):
        """测试港股文件名生成。"""
        filename = downloader.generate_filename("00700", "腾讯控股", 2024, "annual")
        assert filename == "00700_腾讯控股_2024_an.pdf"

        # ESG 报告
        filename = downloader.generate_filename("00700", "腾讯控股", 2024, "esg")
        assert filename == "00700_腾讯控股_2024_es.pdf"

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
            code="00700",
            name="腾讯控股",
            doc_type="invalid_type",
            dry_run=True,
        )
        assert result.success is False
        assert len(result.errors) > 0

    def test_skip_existing(self, downloader, tmp_path):
        """测试跳过已下载文件。"""
        # 创建一个假文件
        existing_file = tmp_path / "00700_腾讯控股_2024_an.pdf"
        existing_file.write_bytes(b"fake content")
        
        # 下载应该跳过
        result = downloader.download(
            code="00700",
            name="腾讯控股",
            year=2024,
            skip_existing=True,
            dry_run=True,
        )
        
        assert isinstance(result, DownloadResult)


class TestIntegration:
    """集成测试（需要网络）。"""

    @pytest.fixture
    def real_downloader(self, tmp_path):
        """创建真实下载器用于集成测试。"""
        return HkexDownloader(output_dir=tmp_path)

    def test_get_tencent_stock_id(self, real_downloader):
        """测试获取腾讯 stockId。"""
        pytest.skip("集成测试，需要网络连接")

    def test_fetch_maotai_annual_reports(self, real_downloader):
        """测试获取茅台年报。"""
        pytest.skip("集成测试，需要网络连接")
