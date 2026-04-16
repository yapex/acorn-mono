"""Abstract base class for financial report downloaders."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class DownloadResult:
    """Result of a download operation."""

    success: bool
    files: list[Path] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    def __bool__(self) -> bool:
        return self.success

    def add_file(self, path: Path) -> None:
        """Add a downloaded file to the result."""
        self.files.append(path)

    def add_error(self, error: str) -> None:
        """Add an error message to the result."""
        self.errors.append(error)

    @property
    def total_size(self) -> int:
        """Calculate total size of downloaded files in bytes."""
        return sum(f.stat().st_size for f in self.files if f.exists())

    @property
    def total_size_mb(self) -> float:
        """Calculate total size of downloaded files in MB."""
        return self.total_size / 1024 / 1024


class BaseDownloader(ABC):
    """Abstract base class for all financial report downloaders."""

    # Market identifier (e.g., 'cn', 'hk', 'us')
    market: str = ""

    # Supported document types
    SUPPORTED_TYPES: list[str] = []

    def __init__(self, output_dir: Optional[Path] = None):
        """
        Initialize the downloader.

        Args:
            output_dir: Directory to save downloaded files.
        """
        self.output_dir = output_dir or self._get_default_output_dir()

    @abstractmethod
    def download(
        self,
        code: str,
        name: str,
        years: int = 10,
        year: Optional[int] = None,
        doc_type: str = "annual",
        dry_run: bool = False,
        skip_existing: bool = True,
    ) -> DownloadResult:
        """
        Download financial reports.

        Args:
            code: Stock code
            name: Company name (for filename)
            years: Number of recent years to download
            year: Specific year to download
            doc_type: Document type
            dry_run: List only, no download
            skip_existing: Skip already downloaded files

        Returns:
            DownloadResult with downloaded files and metadata
        """
        pass

    @abstractmethod
    def get_supported_types(self) -> list[str]:
        """Return list of supported document types."""
        pass

    @abstractmethod
    def _get_default_output_dir(self) -> Path:
        """Get default output directory for this market."""
        pass

    def validate_code(self, code: str) -> bool:
        """Validate stock code format."""
        return bool(code and code.strip())

    def generate_filename(
        self,
        code: str,
        name: str,
        year: int,
        doc_type: str,
        extension: str = "pdf",
    ) -> str:
        """
        Generate standardized filename.

        Format: {code}_{name}_{year}_{type}.{ext}
        
        Type mapping (2 letters):
        - annual → an
        - 20-F → 2f
        - 10-K → 1k
        - 10-Q → 1q
        - 8-K → 8k
        """
        safe_name = name.replace(" ", "_").replace("/", "_")

        # Type map (统一为 2 个字母)
        type_map = {
            "annual": "an",
            "ipo": "ip",
            "listing": "li",
            "bond": "bo",
            "esg": "es",
            "20-F": "2f",
            "10-K": "1k",
            "10-Q": "1q",
            "8-K": "8k",
        }
        suffix = type_map.get(doc_type, doc_type.lower().replace("-", "")[:2])

        return f"{code}_{safe_name}_{year}_{suffix}.{extension}"
