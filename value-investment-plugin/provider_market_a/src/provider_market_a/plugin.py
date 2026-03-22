"""Provider A Plugin (Tushare) for pluggy

Provides:
- A股市场数据获取
- 支持财务报表、财务指标、市场数据

字段定义从 FIELD_MAPPINGS 动态计算，不再硬编码。
"""
from __future__ import annotations

from typing import Any

from vi_core.spec import vi_hookimpl

from .provider import TushareProvider


# Provider instance (lazy init)
_provider: TushareProvider | None = None


def _get_provider() -> TushareProvider:
    """Get or create TushareProvider instance"""
    global _provider
    if _provider is None:
        _provider = TushareProvider()
    return _provider


class ProviderAPlugin:
    """A-Share market data provider plugin"""

    @vi_hookimpl
    def vi_markets(self) -> list[str]:
        """Return supported markets"""
        return ["A"]

    @vi_hookimpl
    def vi_supported_fields(self) -> list[str]:
        """Return list of supported fields

        从 FIELD_MAPPINGS 动态计算，返回 Provider 实际能从 Tushare API
        获取的所有系统标准字段。
        """
        return list(TushareProvider.get_supported_fields())

    @vi_hookimpl
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

    @vi_hookimpl
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

    @vi_hookimpl
    def vi_fetch_market(
        self,
        symbol: str,
        fields: set[str],
    ) -> dict[str, Any]:
        """Fetch market data"""
        provider = _get_provider()
        return provider.fetch_market(symbol, fields)

    @vi_hookimpl
    def vi_fetch_historical(
        self,
        symbol: str,
        start_date: str | None = None,
        end_date: str | None = None,
        adjust: str = "",
    ) -> dict[str, Any] | None:
        """Fetch historical trading data (OHLCV) for A-share
        
        Args:
            symbol: Stock code (e.g. "600519", "000001")
            start_date: Start date in "YYYY-MM-DD" format (optional)
            end_date: End date in "YYYY-MM-DD" format (optional)
            adjust: Price adjustment method
                - "": No adjustment (不复权)
                - "qfq": Forward adjustment (前复权)
                - "hfq": Backward adjustment (后复权)
        
        Returns:
            {
                "date": [...],
                "open": [...],
                "high": [...],
                "low": [...],
                "close": [...],
                "volume": [...],
                "amount": [...],
            }
            or None if not supported
        """
        provider = _get_provider()
        df = provider.fetch_historical(symbol, start_date, end_date, adjust)
        if df is None or df.empty:
            return None
        
        # 转换 DataFrame 为 dict
        return df.to_dict(orient="list")


# Plugin instance for pluggy registration
plugin = ProviderAPlugin()
