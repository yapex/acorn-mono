"""Tests for PDF to TXT converter."""
import pytest
from pathlib import Path
from pdf2txt.extractor import (
    PdfExtractor,
    parse_company_name,
    parse_report_type,
    parse_year,
    REPORT_TYPE_SUFFIXES,
)


class TestParseCompanyName:
    """Test cases for parse_company_name function."""

    def test_parse_standard_format(self):
        """Test parsing standard filename format."""
        path = Path("600519_贵州茅台_2023_an.pdf")
        assert parse_company_name(path) == "贵州茅台"

    def test_parse_with_stock_code_hk(self):
        """Test parsing HK stock format."""
        path = Path("09961_携程集团_2023_an.pdf")
        assert parse_company_name(path) == "携程集团"

    def test_parse_fallback_single_part(self):
        """Test fallback when filename has no underscores."""
        path = Path("report.pdf")
        assert parse_company_name(path) == "report"

    def test_parse_fallback_two_parts(self):
        """Test fallback with only one underscore."""
        path = Path("company_report.pdf")
        assert parse_company_name(path) == "company_report"

    def test_parse_company_name_with_underscores(self):
        """Test parsing company name that contains underscores."""
        path = Path("600519_贵州茅台_集团_2023_an.pdf")
        assert parse_company_name(path) == "贵州茅台_集团"

    def test_parse_es_report_format(self):
        """Test parsing ESG/sustainability report format (_es suffix)."""
        path = Path("00700_腾讯控股_2024_es.pdf")
        assert parse_company_name(path) == "腾讯控股"

    def test_parse_all_report_types(self):
        """Test parsing all supported report types."""
        test_cases = [
            ("00700_腾讯控股_2024_an.pdf", "腾讯控股", "annual", "2024"),
            ("00700_腾讯控股_2024_es.pdf", "腾讯控股", "esg", "2024"),
            ("00700_腾讯控股_2024_H1.pdf", "腾讯控股", "interim", "2024"),
            ("00700_腾讯控股_2024_fs.pdf", "腾讯控股", "financial", "2024"),
            ("00700_腾讯控股_2024_ci.pdf", "腾讯控股", "circular", "2024"),
            ("00700_腾讯控股_2018_ip.pdf", "腾讯控股", "prospectus", "2018"),
        ]
        for filename, expected_company, expected_type, expected_year in test_cases:
            path = Path(filename)
            assert parse_company_name(path) == expected_company
            assert parse_report_type(path) == expected_type
            assert parse_year(path) == expected_year

    def test_parse_report_type_unknown(self):
        """Test parsing unknown report type."""
        path = Path("00700_腾讯控股_2024_xx.pdf")
        assert parse_report_type(path) is None

    def test_parse_year_invalid(self):
        """Test parsing invalid year format."""
        path = Path("report_2024.pdf")
        assert parse_year(path) is None


class TestPdfExtractor:
    """Test cases for PdfExtractor class."""

    def test_extractor_init(self):
        """Test extractor initialization."""
        extractor = PdfExtractor()
        assert extractor is not None
        assert extractor.output_dir is None
        assert extractor.organize_by_company is False

    def test_extractor_with_output_dir(self, tmp_path):
        """Test extractor with custom output directory."""
        extractor = PdfExtractor(output_dir=tmp_path)
        assert extractor.output_dir == tmp_path

    def test_extractor_with_organize_by_company(self, tmp_path):
        """Test extractor with organize_by_company enabled."""
        extractor = PdfExtractor(output_dir=tmp_path, organize_by_company=True)
        assert extractor.organize_by_company is True

    def test_extract_nonexistent_file(self):
        """Test extraction with non-existent file raises error."""
        extractor = PdfExtractor()
        with pytest.raises(FileNotFoundError):
            extractor.extract("/nonexistent/file.pdf")

    def test_extract_invalid_extension(self, tmp_path):
        """Test extraction with non-PDF file raises error."""
        fake_pdf = tmp_path / "file.txt"
        fake_pdf.write_text("not a pdf")
        extractor = PdfExtractor()
        with pytest.raises(ValueError, match="PDF"):
            extractor.extract(fake_pdf)

    def test_get_output_path(self, tmp_path):
        """Test output path calculation."""
        pdf_file = tmp_path / "annual_report_2024.pdf"
        pdf_file.write_bytes(b"%PDF-fake")
        
        extractor = PdfExtractor(output_dir=tmp_path)
        expected_txt = tmp_path / "annual_report_2024.txt"
        
        assert extractor._get_output_path(pdf_file) == expected_txt

    def test_get_output_path_default_to_input_dir(self, tmp_path):
        """Test output path defaults to input directory when no output_dir set."""
        pdf_file = tmp_path / "report.pdf"
        pdf_file.write_bytes(b"%PDF-fake")
        
        extractor = PdfExtractor()
        expected_txt = tmp_path / "report.txt"
        
        assert extractor._get_output_path(pdf_file) == expected_txt

    def test_get_output_path_organize_by_company(self, tmp_path):
        """Test output path with organize_by_company enabled."""
        pdf_file = tmp_path / "600519_贵州茅台_2023_an.pdf"
        pdf_file.write_bytes(b"%PDF-fake")
        
        extractor = PdfExtractor(output_dir=tmp_path, organize_by_company=True)
        expected_txt = tmp_path / "贵州茅台" / "600519_贵州茅台_2023_an.txt"
        
        assert extractor._get_output_path(pdf_file) == expected_txt

    def test_get_output_path_organize_by_company_hk_stock(self, tmp_path):
        """Test output path with HK stock format."""
        pdf_file = tmp_path / "09961_携程集团_2023_an.pdf"
        pdf_file.write_bytes(b"%PDF-fake")
        
        extractor = PdfExtractor(output_dir=tmp_path, organize_by_company=True)
        expected_txt = tmp_path / "携程集团" / "09961_携程集团_2023_an.txt"
        
        assert extractor._get_output_path(pdf_file) == expected_txt
