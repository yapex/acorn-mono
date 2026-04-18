"""Tests for HTML to Markdown converter."""

import pytest
from html2md.converter import HtmlConverter


class TestHtmlConverter:
    """Test HtmlConverter class."""

    def test_extract_company_name_simple(self, tmp_path):
        """Test company name extraction from filename."""
        converter = HtmlConverter()

        # Test standard format
        html_file = tmp_path / "TCOM_携程_2024_an.html"
        html_file.touch()

        company = converter._extract_company_name(html_file)
        assert company == "携程"

    def test_extract_company_name_us_stock(self, tmp_path):
        """Test company name extraction for US stocks."""
        converter = HtmlConverter()

        html_file = tmp_path / "AAPL_Apple_2024_10K.html"
        html_file.touch()

        company = converter._extract_company_name(html_file)
        assert company == "Apple"

    def test_get_output_path_default(self, tmp_path):
        """Test output path with default settings."""
        # Default should use same directory as input file
        converter = HtmlConverter()

        html_file = tmp_path / "test.html"
        html_file.touch()

        output_path = converter._get_output_path(html_file)
        assert output_path == tmp_path / "test.md"

    def test_get_output_path_with_dir(self, tmp_path):
        """Test output path with custom output directory."""
        output_dir = tmp_path / "output"
        converter = HtmlConverter(output_dir=output_dir)

        html_file = tmp_path / "test.html"
        html_file.touch()

        output_path = converter._get_output_path(html_file)
        assert output_path == output_dir / "test.md"

    def test_get_output_path_organize_by_company(self, tmp_path):
        """Test output path with company organization."""
        converter = HtmlConverter(organize_by_company=True)

        html_file = tmp_path / "TCOM_携程_2024_an.html"
        html_file.touch()

        output_path = converter._get_output_path(html_file)
        assert output_path == tmp_path / "携程" / "TCOM_携程_2024_an.md"

    def test_get_output_path_plain_text(self, tmp_path):
        """Test output path with plain text mode."""
        converter = HtmlConverter(plain_text=True)

        html_file = tmp_path / "test.html"
        html_file.touch()

        output_path = converter._get_output_path(html_file)
        assert output_path == tmp_path / "test.txt"
        assert output_path.suffix == ".txt"

    def test_clean_html_removes_ix_tags(self):
        """Test that iXBRL tags are removed."""
        converter = HtmlConverter()

        html = """
        <html>
        <ix:header>
            <ix:hidden>
                <ix:nonNumeric name="test">value</ix:nonNumeric>
            </ix:hidden>
        </ix:header>
        <body>
            <p>Visible content</p>
        </body>
        </html>
        """

        clean = converter._clean_html(html)

        # Should not contain ix: tags
        assert "ix:header" not in clean
        assert "ix:hidden" not in clean
        assert "ix:nonNumeric" not in clean

        # Should contain visible content
        assert "Visible content" in clean

    def test_clean_html_removes_scripts(self):
        """Test that script and style tags are removed."""
        converter = HtmlConverter()

        html = """
        <html>
        <head>
            <script>alert('test');</script>
            <style>.test { color: red; }</style>
        </head>
        <body>Content</body>
        </html>
        """

        clean = converter._clean_html(html)

        assert "<script>" not in clean
        assert "<style>" not in clean
        assert "Content" in clean

    def test_should_skip_existing(self, tmp_path):
        """Test skip existing file logic."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        # Create existing output file
        output_file = output_dir / "test.md"
        output_file.touch()

        converter = HtmlConverter(
            output_dir=output_dir,
            skip_existing=True,
        )

        html_file = tmp_path / "test.html"
        html_file.touch()

        assert converter._should_skip(html_file) is True

    def test_should_not_skip_when_force(self, tmp_path):
        """Test that force overrides skip."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        # Create existing output file
        output_file = output_dir / "test.md"
        output_file.touch()

        converter = HtmlConverter(
            output_dir=output_dir,
            skip_existing=True,
            force=True,
        )

        html_file = tmp_path / "test.html"
        html_file.touch()

        assert converter._should_skip(html_file) is False

    def test_convert_nonexistent_file(self, tmp_path):
        """Test conversion of nonexistent file raises error."""
        converter = HtmlConverter()

        html_file = tmp_path / "nonexistent.html"

        with pytest.raises(FileNotFoundError):
            converter.convert(html_file)
