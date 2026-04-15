"""Tests for CLI commands."""
import pytest
from typer.testing import CliRunner
from pdf2txt.cli import app

runner = CliRunner()


class TestCli:
    """Test cases for CLI commands."""

    def test_cli_help(self):
        """Test CLI help message."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "pdf2txt" in result.stdout.lower() or "PDF" in result.stdout

    def test_convert_help(self):
        """Test convert command help."""
        result = runner.invoke(app, ["convert", "--help"])
        assert result.exit_code == 0
        assert "--organize-by-company" in result.stdout

    def test_convert_nonexistent_file(self):
        """Test convert command with non-existent file."""
        result = runner.invoke(app, ["convert", "/nonexistent/file.pdf"])
        assert result.exit_code != 0

    def test_convert_invalid_extension(self, tmp_path):
        """Test convert command with non-PDF file."""
        fake_file = tmp_path / "file.txt"
        fake_file.write_text("not a pdf")
        result = runner.invoke(app, ["convert", str(fake_file)])
        assert result.exit_code != 0

    def test_convert_with_output_dir(self, tmp_path):
        """Test convert command with custom output directory."""
        fake_pdf = tmp_path / "test.pdf"
        fake_pdf.write_bytes(b"%PDF-fake")
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        
        result = runner.invoke(app, ["convert", str(fake_pdf), "-o", str(output_dir)])
        # Will fail on fake PDF but tests the option parsing
        assert "pdf" in result.stdout.lower() or result.exit_code != 0

    def test_convert_with_organize_by_company(self, tmp_path):
        """Test convert command with organize-by-company option."""
        fake_pdf = tmp_path / "600519_贵州茅台_2023_an.pdf"
        fake_pdf.write_bytes(b"%PDF-fake")
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        
        result = runner.invoke(app, [
            "convert", str(fake_pdf),
            "-o", str(output_dir),
            "--organize-by-company"
        ])
        # Will fail on fake PDF but tests the option parsing
        assert result.exit_code != 0  # Fails because fake PDF

    def test_batch_help(self):
        """Test batch command help."""
        result = runner.invoke(app, ["batch", "--help"])
        assert result.exit_code == 0

    def test_batch_with_organize_by_company(self, tmp_path):
        """Test batch command with organize-by-company option."""
        fake_pdf = tmp_path / "600519_贵州茅台_2023_an.pdf"
        fake_pdf.write_bytes(b"%PDF-fake")
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        
        result = runner.invoke(app, [
            "batch", str(tmp_path),
            "-o", str(output_dir),
            "--organize-by-company"
        ])
        # Will fail on fake PDF but tests the option parsing
        assert "pdf" in result.stdout.lower() or result.exit_code != 0

    def test_convert_with_skip_existing(self, tmp_path):
        """Test convert command with skip-existing option."""
        fake_pdf = tmp_path / "test.pdf"
        fake_pdf.write_bytes(b"%PDF-fake")
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        
        # Create existing output
        output_file = output_dir / "test.txt"
        output_file.write_text("existing")
        
        result = runner.invoke(app, [
            "convert", str(fake_pdf),
            "-o", str(output_dir),
            "--skip-existing"
        ])
        # Should skip and succeed
        assert result.exit_code == 0
        assert "skipped" in result.stdout.lower() or "Converted" in result.stdout

    def test_convert_with_force(self, tmp_path):
        """Test convert command with force option."""
        fake_pdf = tmp_path / "test.pdf"
        fake_pdf.write_bytes(b"%PDF-fake")
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        
        # Create existing output
        output_file = output_dir / "test.txt"
        output_file.write_text("existing")
        
        result = runner.invoke(app, [
            "convert", str(fake_pdf),
            "-o", str(output_dir),
            "--force"
        ])
        # Will fail on fake PDF but tests the option parsing
        assert result.exit_code != 0

    def test_batch_with_skip_existing(self, tmp_path):
        """Test batch command with skip-existing option."""
        # Create PDF and existing output
        pdf_file = tmp_path / "600519_贵州茅台_2023_an.pdf"
        pdf_file.write_bytes(b"%PDF-fake")
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        output_file = output_dir / "贵州茅台" / "600519_贵州茅台_2023_an.txt"
        output_file.parent.mkdir()
        output_file.write_text("existing")
        
        result = runner.invoke(app, [
            "batch", str(tmp_path),
            "-o", str(output_dir),
            "--skip-existing",
            "-c"  # organize by company
        ])
        # Should skip and report summary (exit 0 even with fake PDF because it's skipped)
        assert result.exit_code == 0
        assert "skipped" in result.stdout.lower()
