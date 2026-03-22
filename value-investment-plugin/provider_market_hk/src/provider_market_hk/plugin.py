"""Provider Market HK Plugin for pluggy

Provides:
- 港股市场数据获取
- 支持财务报表、财务指标、市场数据

字段定义从 FIELD_MAPPINGS 动态计算。
"""
from __future__ import annotations

from typing import Any

import pandas as pd

from vi_core.spec import vi_hookimpl

from .provider import HKProvider


# Provider instance (lazy init)
_provider: HKProvider | None = None


def _get_provider() -> HKProvider:
    """Get or create HKProvider instance"""
    global _provider
    if _provider is None:
        _provider = HKProvider()
    return _provider


class ProviderHKPlugin:
    """HK market data provider plugin"""

    @vi_hookimpl
    def vi_markets(self) -> list[str]:
        """Return supported markets"""
        return ["HK"]

    @vi_hookimpl
    def vi_supported_fields(self) -> list[str]:
        """Return list of supported fields

        从 FIELD_MAPPINGS 动态计算，返回 Provider 实际能从 AKShare API
        获取的所有系统标准字段。
        """
        return list(HKProvider.get_supported_fields())

    @vi_hookimpl
    def vi_fetch_financials(
        self,
        symbol: str,
        fields: set[str],
        end_year: int,
        years: int = 10,
    ) -> pd.DataFrame | None:
        """Fetch financial statement data"""
        provider = _get_provider()
        return provider.fetch_financials(symbol, fields, end_year, years)

    @vi_hookimpl
    def vi_fetch_indicators(
        self,
        symbol: str,
        fields: set[str],
        end_year: int,
        years: int = 10,
    ) -> pd.DataFrame | None:
        """Fetch financial indicators"""
        provider = _get_provider()
        return provider.fetch_indicators(symbol, fields, end_year, years)

    @vi_hookimpl
    def vi_fetch_market(
        self,
        symbol: str,
        fields: set[str],
    ) -> pd.DataFrame | None:
        """Fetch market data"""
        provider = _get_provider()
        return provider.fetch_market(symbol, fields)

    @vi_hookimpl
    def vi_fetch_historical(
        self,
        symbol: str,
        start_date: str | None = None,
        end_date: str | None = None,
        adjust: str = "hfq",
    ) -> pd.DataFrame | None:
        """Fetch historical trading data (OHLCV)"""
        provider = _get_provider()
        return provider.fetch_historical(symbol, start_date, end_date, adjust)


# Plugin instance for pluggy registration
plugin = ProviderHKPlugin()
