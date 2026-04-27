"""US Provider Plugin for pluggy

Provides:
- 美股市场数据获取
- 支持历史交易数据

字段定义从 FIELD_MAPPINGS 动态计算，不再硬编码。
"""
from __future__ import annotations


import pandas as pd

from vi_core.spec import vi_hookimpl
from vi_core import SmartCache

from .provider import USProvider


# Provider instance (lazy init)
_provider: USProvider | None = None
_cache: SmartCache | None = None


def _get_provider() -> USProvider:
    """Get or create USProvider instance with cache"""
    global _provider, _cache
    if _provider is None:
        if _cache is None:
            _cache = SmartCache(cache_dir=".cache")
        _provider = USProvider(cache=_cache)
    return _provider
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
        years: int,
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
        years: int,
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
        start_date: str | None,
        end_date: str | None,
        adjust: str,
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

    @vi_hookimpl
    def vi_provide_items(
        self,
        items: list[str],
        symbol: str,
        market: str,
        end_year: int,
        years: int,
    ) -> pd.DataFrame | None:
        """US Provider 实现 vi_provide_items
        
        只响应 US 市场的请求，筛选出支持的字段并获取数据。
        """
        # 市场过滤：只响应 US 市场
        if market != "US":
            return None

        provider = _get_provider()

        # 获取 Provider 支持的所有字段
        supported = provider.get_supported_fields()

        # 筛选出请求中支持的字段
        available = set(items) & supported

        if not available:
            return None

        # 分类字段
        financial_fields = set()
        indicator_fields = set()
        market_fields = set()

        # 从 FIELD_MAPPINGS 中分类
        for category, mapping in provider.FIELD_MAPPINGS.items():
            category_fields = set(mapping.values())
            if category in ["balance_sheet", "income_statement", "cash_flow"]:
                financial_fields.update(category_fields)
            elif category == "indicators":
                indicator_fields.update(category_fields)
            elif category == "market":
                market_fields.update(category_fields)

        # 筛选出各类别中请求的字段
        request_financial = available & financial_fields
        request_indicators = available & indicator_fields
        request_market = available & market_fields

        # 收集 DataFrames
        dfs: list[pd.DataFrame] = []

        # 获取财务数据
        if request_financial:
            df = provider.fetch_financials(symbol, request_financial, end_year, years)
            if df is not None and not df.empty:
                dfs.append(df)

        # 获取指标数据
        if request_indicators:
            df = provider.fetch_indicators(symbol, request_indicators, end_year, years)
            if df is not None and not df.empty:
                dfs.append(df)

        # 获取市场数据
        if request_market:
            df = provider.fetch_market(symbol, request_market)
            if df is not None and not df.empty:
                dfs.append(df)

        # 合并数据
        if not dfs:
            return None

        return self._merge_dfs(dfs)

    def _merge_dfs(self, dfs: list[pd.DataFrame]) -> pd.DataFrame | None:
        """合并多个 DataFrame"""
        if not dfs:
            return None

        fiscal_year = "fiscal_year"
        result = dfs[0].copy()

        # 确保 fiscal_year 是 index
        if fiscal_year in result.columns:
            result = result.set_index(fiscal_year)

        for df in dfs[1:]:
            if df is None or df.empty:
                continue

            df_to_merge = df.copy()
            if fiscal_year in df_to_merge.columns:
                df_to_merge = df_to_merge.set_index(fiscal_year)

            # 找出新列
            cols_to_add = [c for c in df_to_merge.columns if c not in result.columns]
            if not cols_to_add:
                continue

            # 单行数据广播
            if len(df_to_merge) == 1:
                for col in cols_to_add:
                    result[col] = df_to_merge[col].iloc[0]
            else:
                result = result.merge(
                    df_to_merge[cols_to_add],
                    left_index=True,
                    right_index=True,
                    how="left"
                )

        return result


# Plugin instance for pluggy registration
plugin = ProviderUSPlugin()
