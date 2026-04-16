"""HTML to Markdown converter for SEC filings."""

import re
from pathlib import Path
from typing import Optional

from bs4 import BeautifulSoup, Comment
from html_to_markdown import convert, ConversionOptions
from loguru import logger


class HtmlConverter:
    """Convert SEC HTML filings to Markdown format."""

    def __init__(
        self,
        output_dir: Optional[Path] = None,
        organize_by_company: bool = False,
        skip_existing: bool = False,
        force: bool = False,
        plain_text: bool = False,
    ) -> None:
        """Initialize the converter.

        Args:
            output_dir: Output directory (default: same as input file)
            organize_by_company: Organize output by company name
            skip_existing: Skip conversion if output file exists
            force: Force conversion even if output file exists
            plain_text: Output plain text instead of Markdown
        """
        self.output_dir = output_dir
        self.organize_by_company = organize_by_company
        self.skip_existing = skip_existing
        self.force = force
        self.plain_text = plain_text

    def _get_output_path(self, html_file: Path) -> Path:
        """Determine the output file path."""
        if self.output_dir:
            output_dir = self.output_dir
        else:
            # Default to outputs/ directory in current working directory
            output_dir = Path.cwd() / "outputs"

        # Extract company name from filename if organizing by company
        if self.organize_by_company:
            company_name = self._extract_company_name(html_file)
            if company_name:
                output_dir = output_dir / company_name

        # Determine output extension
        ext = ".txt" if self.plain_text else ".md"
        output_filename = html_file.stem + ext

        return output_dir / output_filename

    def _extract_company_name(self, html_file: Path) -> str:
        """Extract company name from HTML filename.

        Expected format: <code>_<company_name>_<year>_<type>.html
        Example: TCOM_携程_2024_an.html → 携程
        """
        name = html_file.stem
        parts = name.split("_")
        if len(parts) >= 2:
            # Return everything between code and year
            # e.g., "TCOM_携程_2024_an" → "携程"
            return parts[1] if len(parts) > 2 else parts[0]
        return name

    def _clean_html(self, content: str) -> str:
        """Clean SEC iXBRL HTML by removing XBRL metadata.

        Args:
            content: Raw HTML content

        Returns:
            Cleaned HTML with XBRL tags removed
        """
        # Parse with BeautifulSoup
        soup = BeautifulSoup(content, "lxml")

        # 1. Remove ix:header (hidden XBRL metadata)
        for tag_name in ["ix:header", "ix:references", "ix:resources"]:
            for header in soup.find_all(tag_name):
                header.decompose()

        # 2. Unwrap all ix:* tags (remove tags but keep content)
        for tag in soup.find_all(lambda t: t.name and t.name.startswith("ix:")):
            tag.unwrap()

        # 3. Remove script and style tags
        for tag in soup.find_all(["script", "style"]):
            tag.decompose()

        # 4. Remove HTML comments
        for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
            comment.extract()

        return str(soup)

    def _should_skip(self, html_file: Path) -> bool:
        """Check if conversion should be skipped."""
        if not self.skip_existing or self.force:
            return False

        output_path = self._get_output_path(html_file)
        return output_path.exists()

    def convert(self, html_file: Path) -> Path:
        """Convert an HTML file to Markdown.

        Args:
            html_file: Path to the HTML file

        Returns:
            Path to the output file

        Raises:
            FileNotFoundError: If the input file doesn't exist
            ValueError: If the file is not valid HTML
        """
        if not html_file.exists():
            raise FileNotFoundError(f"HTML file not found: {html_file}")

        # Check if should skip
        if self._should_skip(html_file):
            output_path = self._get_output_path(html_file)
            logger.info(f"Skipping {html_file.name} (already exists)")
            return output_path

        logger.debug(f"Reading {html_file}")
        with open(html_file, "r", encoding="utf-8") as f:
            content = f.read()

        logger.debug(f"Original HTML size: {len(content):,} chars")

        # Clean the HTML
        logger.debug("Cleaning iXBRL metadata...")
        clean_html = self._clean_html(content)
        logger.debug(f"Cleaned HTML size: {len(clean_html):,} chars")

        # Convert to Markdown
        logger.debug("Converting to Markdown...")
        options = ConversionOptions(
            extract_metadata=False,
            heading_style="atx",
            wrap=True,
            wrap_width=120,
        )

        if self.plain_text:
            options.output_format = "plain"

        result = convert(clean_html, options)
        logger.debug(f"Markdown size: {len(result.content):,} chars")

        # Create output directory
        output_path = self._get_output_path(html_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Write output
        ext = ".txt" if self.plain_text else ".md"
        logger.debug(f"Writing {ext} to {output_path}")
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(result.content)

        return output_path
