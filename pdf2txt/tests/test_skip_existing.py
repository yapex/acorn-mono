"""Tests for skip existing converted files functionality."""
import pytest
from pathlib import Path
from pdf2txt.extractor import PdfExtractor, should_skip_conversion


class TestShouldSkipConversion:
    """Test cases for should_skip_conversion function."""

    def test_skip_when_output_exists(self, tmp_path):
        """Test that conversion is skipped when output file exists."""
        pdf_file = tmp_path / "report.pdf"
        pdf_file.write_bytes(b"%PDF-fake")
        
        # Create existing output file
        output_file = tmp_path / "report.txt"
        output_file.write_text("existing content")
        
        extractor = PdfExtractor(output_dir=tmp_path)
        assert should_skip_conversion(pdf_file, extractor) is True

    def test_not_skip_when_output_not_exists(self, tmp_path):
        """Test that conversion proceeds when output file doesn't exist."""
        pdf_file = tmp_path / "report.pdf"
        pdf_file.write_bytes(b"%PDF-fake")
        
        extractor = PdfExtractor(output_dir=tmp_path)
        assert should_skip_conversion(pdf_file, extractor) is False

    def test_not_skip_when_output_empty(self, tmp_path):
        """Test that conversion proceeds when output file is empty (likely failed conversion)."""
        pdf_file = tmp_path / "report.pdf"
        pdf_file.write_bytes(b"%PDF-fake")
        
        # Create empty output file
        output_file = tmp_path / "report.txt"
        output_file.write_text("")
        
        extractor = PdfExtractor(output_dir=tmp_path)
        # Empty file should NOT be skipped (re-convert)
        assert should_skip_conversion(pdf_file, extractor) is False

    def test_force_flag_in_extract_method(self, tmp_path):
        """Test that force flag is handled in extract() method, not should_skip_conversion()."""
        pdf_file = tmp_path / "report.pdf"
        pdf_file.write_bytes(b"%PDF-fake")
        
        # Create existing output file
        output_file = tmp_path / "report.txt"
        output_file.write_text("existing content")
        
        # should_skip_conversion only checks file existence, not force flag
        extractor_no_force = PdfExtractor(output_dir=tmp_path)
        assert should_skip_conversion(pdf_file, extractor_no_force) is True
        
        # force flag is checked in extract() method
        extractor_with_force = PdfExtractor(output_dir=tmp_path, force=True)
        # should_skip_conversion still returns True, but extract() will ignore it
        assert should_skip_conversion(pdf_file, extractor_with_force) is True

    def test_skip_with_organize_by_company(self, tmp_path):
        """Test skip logic with organize_by_company enabled."""
        pdf_file = tmp_path / "600519_贵州茅台_2023_an.pdf"
        pdf_file.write_bytes(b"%PDF-fake")
        
        # Create existing output file in company subdirectory
        output_dir = tmp_path / "贵州茅台"
        output_dir.mkdir()
        output_file = output_dir / "600519_贵州茅台_2023_an.txt"
        output_file.write_text("existing content")
        
        extractor = PdfExtractor(output_dir=tmp_path, organize_by_company=True)
        assert should_skip_conversion(pdf_file, extractor) is True


class TestExtractorSkipBehavior:
    """Test cases for PdfExtractor skip behavior."""

    def test_extract_skips_existing(self, tmp_path):
        """Test that extract() skips existing files and returns output path."""
        pdf_file = tmp_path / "report.pdf"
        pdf_file.write_bytes(b"%PDF-fake")
        
        # Create existing output file
        output_file = tmp_path / "report.txt"
        original_content = "existing content"
        output_file.write_text(original_content)
        
        extractor = PdfExtractor(output_dir=tmp_path, skip_existing=True)
        result_path = extractor.extract(pdf_file)
        
        # Should return the output path without modifying content
        assert result_path == output_file
        assert output_file.read_text() == original_content

    def test_extract_processes_non_existing(self, tmp_path):
        """Test that extract() processes files when output doesn't exist."""
        pdf_file = tmp_path / "report.pdf"
        # Don't create output file
        
        extractor = PdfExtractor(output_dir=tmp_path, skip_existing=True)
        
        # Should raise error on fake PDF, but that's expected
        with pytest.raises(Exception):  # Extractous will fail on fake PDF
            extractor.extract(pdf_file)

    def test_extract_force_overrides_skip(self, tmp_path):
        """Test that force=True overrides skip_existing."""
        pdf_file = tmp_path / "report.pdf"
        pdf_file.write_bytes(b"%PDF-fake")
        
        # Create existing output file
        output_file = tmp_path / "report.txt"
        original_content = "existing content"
        output_file.write_text(original_content)
        
        # force=True should override skip_existing=True
        extractor = PdfExtractor(output_dir=tmp_path, skip_existing=True, force=True)
        
        # Should attempt conversion (will fail on fake PDF)
        with pytest.raises(Exception):
            extractor.extract(pdf_file)


class TestBatchSkipBehavior:
    """Test cases for batch conversion skip behavior."""

    def test_batch_skip_summary(self, tmp_path):
        """Test that batch conversion reports skipped files."""
        # Create multiple PDF files
        pdf1 = tmp_path / "report1.pdf"
        pdf2 = tmp_path / "report2.pdf"
        pdf1.write_bytes(b"%PDF-fake")
        pdf2.write_bytes(b"%PDF-fake")
        
        # Create output for only one file
        output1 = tmp_path / "report1.txt"
        output1.write_text("existing")
        
        extractor = PdfExtractor(output_dir=tmp_path, skip_existing=True)
        
        # Get list of files to process
        pdf_files = list(tmp_path.glob("*.pdf"))
        
        skipped = 0
        to_process = 0
        for pdf_file in pdf_files:
            if should_skip_conversion(pdf_file, extractor):
                skipped += 1
            else:
                to_process += 1
        
        assert skipped == 1
        assert to_process == 1

    def test_batch_skip_with_company_organization(self, tmp_path):
        """Test batch skip with organize_by_company."""
        # Create PDFs from different companies
        moutai_pdf = tmp_path / "600519_贵州茅台_2023_an.pdf"
        ctrip_pdf = tmp_path / "09961_携程集团_2023_an.pdf"
        moutai_pdf.write_bytes(b"%PDF-fake")
        ctrip_pdf.write_bytes(b"%PDF-fake")
        
        # Create output for only Moutai
        moutai_dir = tmp_path / "贵州茅台"
        moutai_dir.mkdir()
        moutai_output = moutai_dir / "600519_贵州茅台_2023_an.txt"
        moutai_output.write_text("existing")
        
        extractor = PdfExtractor(output_dir=tmp_path, organize_by_company=True, skip_existing=True)
        
        # Check skip logic for each file
        assert should_skip_conversion(moutai_pdf, extractor) is True
        assert should_skip_conversion(ctrip_pdf, extractor) is False
