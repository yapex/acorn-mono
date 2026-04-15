"""PDF to TXT extraction using Extractous."""

import re
from pathlib import Path
from typing import Optional
from loguru import logger


# Supported report type suffixes
REPORT_TYPE_SUFFIXES = {
    "an": "annual",       # Annual report (年报)
    "es": "esg",          # ESG/Sustainability report (环境、社会及管治报告)
    "H1": "interim",      # Interim/Half-year report (中期报告)
    "fs": "financial",    # Financial statements (财务报表)
    "ci": "circular",     # Circular (通函)
    "ip": "prospectus",   # Prospectus (招股书)
}


def parse_company_name(pdf_path: Path) -> str:
    """Extract company name from PDF filename.

    Expected format: <stock_code>_<company_name>_<year>_<type>.pdf
    
    Supported types:
        - an: Annual report (年报)
        - es: ESG/Sustainability report (环境、社会及管治报告)
        - H1: Interim/Half-year report (中期报告)
        - fs: Financial statements (财务报表)
        - ci: Circular (通函)
        - ip: Prospectus (招股书)

    Examples:
        - 600519_贵州茅台_2023_an.pdf → 贵州茅台
        - 00700_腾讯控股_2024_es.pdf → 腾讯控股
        - 00700_腾讯控股_2024_H1.pdf → 腾讯控股

    Args:
        pdf_path: Path to the PDF file.

    Returns:
        Company name extracted from filename.
    """
    filename = pdf_path.stem  # e.g., "600519_贵州茅台_2023_an"
    parts = filename.split("_")
    if len(parts) >= 4:
        # Format: <stock_code>_<company_name>_<year>_<type>
        # Company name might contain underscores, so join middle parts
        return "_".join(parts[1:-2])
    # Fallback to full filename if parsing fails
    return filename


def parse_report_type(pdf_path: Path) -> str | None:
    """Extract report type from PDF filename.

    Args:
        pdf_path: Path to the PDF file.

    Returns:
        Report type (e.g., 'annual', 'esg') or None if not recognized.
    """
    filename = pdf_path.stem
    parts = filename.split("_")
    if len(parts) >= 4:
        suffix = parts[-1]
        return REPORT_TYPE_SUFFIXES.get(suffix)
    return None


def parse_year(pdf_path: Path) -> str | None:
    """Extract year from PDF filename.

    Args:
        pdf_path: Path to the PDF file.

    Returns:
        Year as string or None if not found.
    """
    filename = pdf_path.stem
    parts = filename.split("_")
    if len(parts) >= 4:
        year_part = parts[-2]
        # Validate it looks like a year (4 digits)
        if year_part.isdigit() and len(year_part) == 4:
            return year_part
    return None


def should_skip_conversion(pdf_path: Path, extractor: 'PdfExtractor') -> bool:
    """Check if conversion should be skipped because output already exists.

    Args:
        pdf_path: Path to the PDF file.
        extractor: PdfExtractor instance to get output path from.

    Returns:
        True if output file exists and is non-empty, False otherwise.
    """
    output_path = extractor._get_output_path(pdf_path)
    if not output_path.exists():
        return False
    # Skip if output file is non-empty
    return output_path.stat().st_size > 0


class PdfExtractor:
    """Extract text from PDF files using Extractous."""

    def __init__(
        self,
        output_dir: Optional[Path] = None,
        organize_by_company: bool = False,
        skip_existing: bool = False,
        force: bool = False,
    ):
        """Initialize the extractor.

        Args:
            output_dir: Output directory for TXT files.
                       If None, outputs to the same directory as the input PDF.
            organize_by_company: If True, organize output files by company name
                                (e.g., output_dir/贵州茅台/xxx.txt).
                                Requires filename format: <code>_<name>_<year>_an.pdf
            skip_existing: If True, skip conversion when output file already exists.
            force: If True, force conversion even if output file exists (overrides skip_existing).
        """
        self.output_dir = output_dir
        self.organize_by_company = organize_by_company
        self.skip_existing = skip_existing
        self.force = force

    def _get_output_path(self, pdf_path: Path) -> Path:
        """Calculate output TXT file path.

        Args:
            pdf_path: Path to the input PDF file.

        Returns:
            Path to the output TXT file.
        """
        output_dir = self.output_dir or pdf_path.parent

        # If organizing by company, add company subdirectory
        if self.organize_by_company:
            company_name = parse_company_name(pdf_path)
            output_dir = output_dir / company_name

        return output_dir / f"{pdf_path.stem}.txt"

    def extract(self, pdf_path: Path | str) -> Path:
        """Extract text from a PDF file.

        Args:
            pdf_path: Path to the PDF file.

        Returns:
            Path to the extracted TXT file.

        Raises:
            FileNotFoundError: If the PDF file does not exist.
            ValueError: If the file is not a PDF.
        """
        pdf_path = Path(pdf_path)

        # Validate input
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        if pdf_path.suffix.lower() != ".pdf":
            raise ValueError(f"Expected PDF file, got: {pdf_path.suffix}")

        # Check if should skip
        if self.skip_existing and not self.force:
            if should_skip_conversion(pdf_path, self):
                output_path = self._get_output_path(pdf_path)
                logger.info(f"Skipping (already exists): {pdf_path} → {output_path}")
                return output_path

        # Import extractous here to avoid dependency issues if not installed
        try:
            from extractous import Extractor
        except ImportError:
            raise ImportError("extractous not installed. Run: pip install extractous")

        # Extract text
        logger.info(f"Extracting text from: {pdf_path}")
        extractor_obj = Extractor()
        # extract_file_to_string returns (text, metadata)
        text_content, _ = extractor_obj.extract_file_to_string(str(pdf_path))

        # Write output
        output_path = self._get_output_path(pdf_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(text_content, encoding="utf-8")

        logger.info(f"Text extracted to: {output_path}")
        return output_path


def convert_pdf_to_txt(
    pdf_path: Path | str,
    output_dir: Optional[Path | str] = None,
    organize_by_company: bool = False,
    skip_existing: bool = False,
    force: bool = False,
) -> Path:
    """Convenience function to convert a single PDF to TXT.

    Args:
        pdf_path: Path to the PDF file.
        output_dir: Optional output directory.
        organize_by_company: If True, organize output by company name.
        skip_existing: If True, skip conversion when output file already exists.
        force: If True, force conversion even if output file exists.

    Returns:
        Path to the extracted TXT file.
    """
    extractor = PdfExtractor(
        output_dir=Path(output_dir) if output_dir else None,
        organize_by_company=organize_by_company,
        skip_existing=skip_existing,
        force=force,
    )
    return extractor.extract(pdf_path)
