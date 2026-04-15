"""Integration tests for PDF to TXT converter.

These tests use actual PDF files from the downloads directory.
"""
import pytest
from pathlib import Path
from pdf2txt.extractor import PdfExtractor, convert_pdf_to_txt, parse_company_name

# Path to test fixtures (downloads directory)
DOWNLOADS_DIR = Path(__file__).parent.parent / "downloads"


@pytest.fixture
def sample_moutai_pdf() -> Path | None:
    """Get path to Moutai PDF if available."""
    pdf_file = DOWNLOADS_DIR / "600519_贵州茅台_2023_an.pdf"
    if pdf_file.exists():
        return pdf_file
    return None


@pytest.fixture
def sample_ctrip_pdf() -> Path | None:
    """Get path to Ctrip PDF if available."""
    pdf_file = DOWNLOADS_DIR / "09961_携程集团_2023_an.pdf"
    if pdf_file.exists():
        return pdf_file
    return None


class TestIntegrationWithRealPDF:
    """Integration tests with actual financial report PDFs."""

    @pytest.mark.skipif(
        not DOWNLOADS_DIR.exists(),
        reason="Downloads directory not available"
    )
    def test_extract_moutai_pdf(self, sample_moutai_pdf, tmp_path):
        """Test extraction with Moutai annual report."""
        if sample_moutai_pdf is None:
            pytest.skip("Moutai PDF not available")
        
        extractor = PdfExtractor(output_dir=tmp_path)
        output_path = extractor.extract(sample_moutai_pdf)
        
        # Verify output exists
        assert output_path.exists()
        assert output_path.suffix == ".txt"
        
        # Verify content is not empty
        content = output_path.read_text(encoding="utf-8")
        assert len(content) > 10000  # Annual reports should be substantial
        
        # Verify expected content
        assert "贵州茅台" in content
        assert "2023" in content
        assert "年度报告" in content

    @pytest.mark.skipif(
        not DOWNLOADS_DIR.exists(),
        reason="Downloads directory not available"
    )
    def test_extract_ctrip_pdf(self, sample_ctrip_pdf, tmp_path):
        """Test extraction with Ctrip annual report."""
        if sample_ctrip_pdf is None:
            pytest.skip("Ctrip PDF not available")
        
        extractor = PdfExtractor(output_dir=tmp_path)
        output_path = extractor.extract(sample_ctrip_pdf)
        
        # Verify output exists
        assert output_path.exists()
        assert output_path.suffix == ".txt"
        
        # Verify content
        content = output_path.read_text(encoding="utf-8")
        assert len(content) > 10000
        # Ctrip PDF uses traditional Chinese: 攜程集團
        assert "攜程集團" in content or "携程集团" in content or "9961" in content

    @pytest.mark.skipif(
        not DOWNLOADS_DIR.exists(),
        reason="Downloads directory not available"
    )
    def test_organize_by_company(self, sample_moutai_pdf, sample_ctrip_pdf, tmp_path):
        """Test organizing output by company name."""
        if sample_moutai_pdf is None or sample_ctrip_pdf is None:
            pytest.skip("PDF files not available")
        
        # Extract both files with organize_by_company=True
        extractor = PdfExtractor(output_dir=tmp_path, organize_by_company=True)
        
        moutai_output = extractor.extract(sample_moutai_pdf)
        ctrip_output = extractor.extract(sample_ctrip_pdf)
        
        # Verify directory structure
        assert moutai_output.parent.name == "贵州茅台"
        assert ctrip_output.parent.name == "携程集团"
        
        # Verify files are in different directories
        assert moutai_output.parent != ctrip_output.parent
        
        # Verify content
        assert "贵州茅台" in moutai_output.read_text(encoding="utf-8")
        # Ctrip PDF uses traditional Chinese: 攜程集團
        ctrip_content = ctrip_output.read_text(encoding="utf-8")
        assert "攜程集團" in ctrip_content or "携程集团" in ctrip_content or "9961" in ctrip_content

    @pytest.mark.skipif(
        not DOWNLOADS_DIR.exists(),
        reason="Downloads directory not available"
    )
    def test_convert_function(self, sample_moutai_pdf, tmp_path):
        """Test convenience function with real PDF."""
        if sample_moutai_pdf is None:
            pytest.skip("Moutai PDF not available")
        
        output_path = convert_pdf_to_txt(sample_moutai_pdf, output_dir=tmp_path)
        
        assert output_path.exists()
        content = output_path.read_text(encoding="utf-8")
        assert "贵州茅台" in content
