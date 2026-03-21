"""Tushare Provider Plugin for pluggy

Provides:
- A股市场数据获取
- 支持财务报表、财务指标、市场数据
"""
from __future__ import annotations

from typing import Any

from vi_core.spec import hookimpl

from .provider import TushareProvider


# Provider instance (lazy init)
_provider: TushareProvider | None = None


def _get_provider() -> TushareProvider:
    """Get or create TushareProvider instance"""
    global _provider
    if _provider is None:
        _provider = TushareProvider()
    return _provider


class TushareProviderPlugin:
    """Tushare data provider plugin"""

    @hookimpl
    def vi_markets(self) -> list[str]:
        """Return supported markets"""
        return ["A"]

    @hookimpl
    def vi_supported_fields(self) -> list[str]:
        """Return list of supported fields"""
        return list(TushareProvider.SUPPORTED_FIELDS)

    @hookimpl
    def vi_fetch_financials(
        self,
        symbol: str,
        fields: set[str],
        end_year: int,
        years: int = 10,
    ) -> dict[str, dict[int, Any]] | None:
        """Fetch financial statement data"""
        provider = _get_provider()
        return provider.fetch_financials(symbol, fields, end_year, years)

    @hookimpl
    def vi_fetch_indicators(
        self,
        symbol: str,
        fields: set[str],
        end_year: int,
        years: int = 10,
    ) -> dict[str, dict[int, Any]] | None:
        """Fetch financial indicators"""
        provider = _get_provider()
        return provider.fetch_indicators(symbol, fields, end_year, years)

    @hookimpl
    def vi_fetch_market(
        self,
        symbol: str,
        fields: set[str],
    ) -> dict[str, Any]:
        """Fetch market data"""
        provider = _get_provider()
        return provider.fetch_market(symbol, fields)


# Plugin instance for pluggy registration
plugin = TushareProviderPlugin()
