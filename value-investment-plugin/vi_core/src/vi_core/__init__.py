"""Value Investment Core

Provides pluggy specs and query engine.
"""
from __future__ import annotations

from .spec import vi_hookspec, vi_hookimpl, ValueInvestmentSpecs
from .plugin import plugin, ViCorePlugin
from .base_provider import BaseDataProvider

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
]
