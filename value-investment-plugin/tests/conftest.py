"""Pytest configuration for value investment plugins tests"""
from __future__ import annotations

import sys
from pathlib import Path

# Add src directories to path for imports
vi_core_src = Path(__file__).parent.parent / "vi_core" / "src"
provider_a_src = Path(__file__).parent.parent / "provider_market_a" / "src"
provider_hk_src = Path(__file__).parent.parent / "provider_market_hk" / "src"
fields_ifrs_src = Path(__file__).parent.parent / "vi_fields_ifrs" / "src"
fields_ext_src = Path(__file__).parent.parent / "vi_fields_extension" / "src"

for src_path in [vi_core_src, provider_a_src, provider_hk_src, fields_ifrs_src, fields_ext_src]:
    if str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))
