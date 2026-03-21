"""Value Investment Core

Provides field registry, calculator registry, and query engine.
"""
from __future__ import annotations

from .spec import hookimpl, hookspec, ValueInvestmentSpecs
from .plugin import plugin, ViCorePlugin

__all__ = [
    # Spec
    "hookspec",
    "hookimpl",
    "ValueInvestmentSpecs",
    # Plugin
    "plugin",
    "ViCorePlugin",
]
