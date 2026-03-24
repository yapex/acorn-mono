"""Pytest configuration for vi_core tests"""
from __future__ import annotations

import sys
from pathlib import Path

# Add src directories to path for imports
root = Path(__file__).parent.parent.parent

src_paths = [
    root / "vi_core" / "src",
    root / "provider_tushare" / "src",
    root / "vi_fields_ifrs" / "src",
    root / "vi_fields_extension" / "src",
    root / "vi_calculators",
    root / "calculators",
]

for src_path in src_paths:
    if str(src_path) not in sys.path and src_path.exists():
        sys.path.insert(0, str(src_path))
