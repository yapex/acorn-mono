"""US Provider Plugin for pluggy

Provides:
- 美股市场数据获取
- 支持历史交易数据

字段定义从 FIELD_MAPPINGS 动态计算，不再硬编码。
"""
from __future__ import annotations

from typing import Any

import pandas as pd

from vi_core.spec import vi_hookimpl

from .provider import USProvider


# Provider instance (lazy init)
_provider: USProvider | None = None


def _get_provider() -> USProvider:
    """Get or create USProvider instance"""
    global _provider
    if _provider is None:
        _provider = USProvider()
    return _provider


class ProviderUSPlugin:
    """US stock market data provider plugin"""

    @vi_hookimpl
    def vi_markets(self) -> list[str]:
        """Return supported markets"""
        return ["US"]

    @vi_hookimpl
    def vi_supported_fields(self) -> list[str]:
        """Return list of supported fields

        从 FIELD_MAPPINGS 动态计算，返回 Provider 实际能从 AKShare API
        获取的所有系统标准字段。
        """
        return list(USProvider.get_supported_fields())

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
        adjust: str = "qfq",
    ) -> pd.DataFrame | None:
        """Fetch historical trading data (OHLCV) for US stock
        
        Args:
            symbol: Stock code (e.g. "AAPL", "GOOGL", "MSFT")
            start_date: Start date in "YYYY-MM-DD" format (optional)
            end_date: End date in "YYYY-MM-DD" format (optional)
            adjust: Price adjustment method (default: "qfq" 前复权)
                - "": No adjustment (不复权)
                - "qfq": Forward adjustment (前复权)
        
        Returns:
            DataFrame with columns: date, open, high, low, close, volume
            or None if not supported
        """
        provider = _get_provider()
        return provider.fetch_historical(symbol, start_date, end_date, adjust)


# Plugin instance for pluggy registration
plugin = ProviderUSPlugin()
