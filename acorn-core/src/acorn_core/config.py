"""
Acorn Configuration System

Configuration loading with layered priorities:
1. Command-line arguments (highest)
2. User config (~/.config/acorn/config.toml)
3. Code defaults (lowest)

Uses XDG Base Directory specification for config location.
"""

import tomllib
from pathlib import Path
from dataclasses import dataclass, field
from typing import Any


def get_user_config_path() -> Path:
    """
    Get user configuration file path following XDG spec.
    
    Returns:
        Path to ~/.config/acorn/config.toml
    """
    # Check XDG_CONFIG_HOME environment variable
    import os
    xdg_config = os.environ.get("XDG_CONFIG_HOME")
    
    if xdg_config:
        base = Path(xdg_config)
    else:
        base = Path.home() / ".config"
    
    return base / "acorn" / "config.toml"


@dataclass
class ViQueryConfig:
    """Configuration for vi query command."""
    years: int = 10
    wacc: float = 0.08
    g_terminal: float = 0.03


@dataclass
class Pdf2txtBatchConfig:
    """Configuration for pdf2txt batch command."""
    output_dir: Path | None = None
    organize_by_company: bool = False
    skip_existing: bool = False


@dataclass
class AcornConfig:
    """
    Acorn configuration container.
    
    Loads configuration from multiple sources with priority:
    1. User config (~/.config/acorn/config.toml)
    2. Code defaults
    """
    vi_query: ViQueryConfig = field(default_factory=ViQueryConfig)
    pdf2txt_batch: Pdf2txtBatchConfig = field(default_factory=Pdf2txtBatchConfig)
    
    # Convenience properties for vi_query
    @property
    def vi_query_years(self) -> int:
        return self.vi_query.years
    
    @property
    def vi_query_wacc(self) -> float:
        return self.vi_query.wacc
    
    @property
    def vi_query_g_terminal(self) -> float:
        return self.vi_query.g_terminal
    
    # Convenience properties for pdf2txt_batch
    @property
    def pdf2txt_batch_output_dir(self) -> Path | None:
        return self.pdf2txt_batch.output_dir
    
    @property
    def pdf2txt_batch_organize_by_company(self) -> bool:
        return self.pdf2txt_batch.organize_by_company
    
    @property
    def pdf2txt_batch_skip_existing(self) -> bool:
        return self.pdf2txt_batch.skip_existing
    
    @classmethod
    def load(cls) -> "AcornConfig":
        """
        Load configuration from user config file.
        
        Returns:
            AcornConfig instance with loaded values
        """
        config_file = get_user_config_path()
        
        if config_file.exists():
            return cls.load_from_file(config_file)
        
        return cls()
    
    @classmethod
    def load_from_file(cls, path: Path) -> "AcornConfig":
        """
        Load configuration from a specific file.
        
        Args:
            path: Path to TOML config file
            
        Returns:
            AcornConfig instance
        """
        data = ConfigLoader._load_file(path)
        return cls.load_from_dict(data)
    
    @classmethod
    def load_from_dict(cls, data: dict[str, Any]) -> "AcornConfig":
        """
        Load configuration from dictionary.
        
        Args:
            data: Configuration dictionary
            
        Returns:
            AcornConfig instance
        """
        config = cls()
        
        # Load vi.query config
        if "vi" in data and "query" in data["vi"]:
            vi_data = data["vi"]["query"]
            if "years" in vi_data:
                config.vi_query.years = int(vi_data["years"])
            if "wacc" in vi_data:
                config.vi_query.wacc = float(vi_data["wacc"])
            if "g_terminal" in vi_data:
                config.vi_query.g_terminal = float(vi_data["g_terminal"])
        
        # Load pdf2txt.batch config
        if "pdf2txt" in data and "batch" in data["pdf2txt"]:
            batch_data = data["pdf2txt"]["batch"]
            if "output_dir" in batch_data:
                config.pdf2txt_batch.output_dir = Path(batch_data["output_dir"])
            if "organize_by_company" in batch_data:
                config.pdf2txt_batch.organize_by_company = bool(batch_data["organize_by_company"])
            if "skip_existing" in batch_data:
                config.pdf2txt_batch.skip_existing = bool(batch_data["skip_existing"])
        
        return config


class ConfigLoader:
    """Configuration file loader utilities."""
    
    @staticmethod
    def _load_file(path: Path) -> dict[str, Any]:
        """
        Load TOML configuration file.
        
        Args:
            path: Path to TOML file
            
        Returns:
            Configuration dictionary, empty dict on error
        """
        if not path.exists():
            return {}
        
        try:
            with open(path, "rb") as f:
                return tomllib.load(f)
        except (tomllib.TOMLDecodeError, IOError):
            return {}
    
    @staticmethod
    def save(config: AcornConfig, path: Path) -> None:
        """
        Save configuration to file.
        
        Args:
            config: AcornConfig instance
            path: Path to save to
        """
        import tomli_w
        
        data = {
            "vi": {
                "query": {
                    "years": config.vi_query.years,
                    "wacc": config.vi_query.wacc,
                    "g_terminal": config.vi_query.g_terminal,
                }
            },
            "pdf2txt": {
                "batch": {
                    "output_dir": str(config.pdf2txt_batch.output_dir) if config.pdf2txt_batch.output_dir else None,
                    "organize_by_company": config.pdf2txt_batch.organize_by_company,
                    "skip_existing": config.pdf2txt_batch.skip_existing,
                }
            }
        }
        
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            tomli_w.dump(data, f)
