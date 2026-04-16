"""Tests for BaseDownloader abstract class."""

import pytest
from pathlib import Path
from financial_downloader.downloaders import BaseDownloader, DownloadResult


class TestDownloadResult:
    """Test DownloadResult dataclass."""

    def test_create_empty_result(self):
        """Test creating an empty download result."""
        result = DownloadResult(success=True)
        
        assert result.success is True
        assert result.files == []
        assert result.errors == []
        assert result.metadata == {}
        assert bool(result) is True

    def test_create_failed_result(self):
        """Test creating a failed download result."""
        result = DownloadResult(
            success=False,
            errors=["Network error", "Timeout"]
        )
        
        assert result.success is False
        assert len(result.errors) == 2
        assert bool(result) is False

    def test_add_file(self, tmp_path):
        """Test adding files to result."""
        result = DownloadResult(success=True)
        test_file = tmp_path / "test.pdf"
        test_file.write_bytes(b"fake pdf content")
        
        result.add_file(test_file)
        
        assert len(result.files) == 1
        assert result.files[0] == test_file

    def test_add_error(self):
        """Test adding errors to result."""
        result = DownloadResult(success=True)
        result.add_error("Connection timeout")
        result.add_error("Retry failed")
        
        assert len(result.errors) == 2
        assert "Connection timeout" in result.errors

    def test_total_size(self, tmp_path):
        """Test calculating total size of downloaded files."""
        result = DownloadResult(success=True)
        
        file1 = tmp_path / "file1.pdf"
        file1.write_bytes(b"x" * 1000)
        
        file2 = tmp_path / "file2.pdf"
        file2.write_bytes(b"x" * 2000)
        
        result.add_file(file1)
        result.add_file(file2)
        
        assert result.total_size == 3000
        assert result.total_size_mb == pytest.approx(3000 / 1024 / 1024, rel=1e-6)


class TestBaseDownloader:
    """Test BaseDownloader abstract class."""

    def test_cannot_instantiate_abstract_class(self):
        """Test that BaseDownloader cannot be instantiated directly."""
        with pytest.raises(TypeError):
            BaseDownloader()

    def test_concrete_implementation_required(self):
        """Test that abstract methods must be implemented."""
        
        class IncompleteDownloader(BaseDownloader):
            pass
        
        with pytest.raises(TypeError):
            IncompleteDownloader()

    def test_complete_implementation(self, tmp_path):
        """Test a complete implementation works."""
        
        class TestDownloader(BaseDownloader):
            market = "test"
            SUPPORTED_TYPES = ["annual", "ipo"]
            
            def download(self, code, name, **kwargs):
                return DownloadResult(success=True)
            
            def get_supported_types(self):
                return self.SUPPORTED_TYPES
            
            def _get_default_output_dir(self):
                return tmp_path
        
        downloader = TestDownloader()
        assert downloader.market == "test"
        assert downloader.get_supported_types() == ["annual", "ipo"]

    def test_generate_filename(self, tmp_path):
        """Test standardized filename generation."""
        
        class TestDownloader(BaseDownloader):
            def download(self, code, name, **kwargs):
                return DownloadResult(success=True)
            
            def get_supported_types(self):
                return []
            
            def _get_default_output_dir(self):
                return tmp_path
        
        downloader = TestDownloader()
        
        filename = downloader.generate_filename(
            "600519", "贵州茅台", 2024, "annual"
        )
        assert filename == "600519_贵州茅台_2024_an.pdf"
        
        filename = downloader.generate_filename(
            "00700", "腾讯控股", 2024, "annual"
        )
        assert filename == "00700_腾讯控股_2024_an.pdf"
        
        filename = downloader.generate_filename(
            "TCOM", "Trip.com", 2024, "20-F"
        )
        assert filename == "TCOM_Trip.com_2024_2f.pdf"
