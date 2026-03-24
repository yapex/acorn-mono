"""Value Investment Core

Provides pluggy specs and query engine.
"""
from __future__ import annotations

from .spec import vi_hookspec, vi_hookimpl, ValueInvestmentSpecs
from .plugin import plugin, ViCorePlugin
from .base_provider import BaseDataProvider, get_ttl_until_april_next_year, get_ttl_until_june_next_year
from .smart_cache import SmartCache

__all__ = [
    # Spec
    "vi_hookspec",
    "vi_hookimpl",
    "ValueInvestmentSpecs",
    # Plugin
    "plugin",
    "ViCorePlugin",
    # Base Provider
    "BaseDataProvider",
    "get_ttl_until_april_next_year",
    "get_ttl_until_june_next_year",
    # Smart Cache
    "SmartCache",
]
