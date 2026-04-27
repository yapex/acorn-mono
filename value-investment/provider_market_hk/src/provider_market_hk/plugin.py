"""Provider Market HK Plugin for pluggy

Provides:
- 港股市场数据获取
- 支持财务报表、财务指标、市场数据

字段定义从 FIELD_MAPPINGS 动态计算。
"""
from __future__ import annotations


import pandas as pd

from vi_core.spec import vi_hookimpl
from vi_core import SmartCache

from .provider import HKProvider


# Provider instance (lazy init)
_provider: HKProvider | None = None
_cache: SmartCache | None = None


def _get_provider() -> HKProvider:
    """Get or create HKProvider instance with cache"""
    global _provider, _cache
    if _provider is None:
        if _cache is None:
            _cache = SmartCache(cache_dir=".cache")
        _provider = HKProvider(cache=_cache)
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
        """Fetch historical trading data (OHLCV)"""
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
        """HK Provider 实现 vi_provide_items
        
        只响应 HK 市场的请求，筛选出支持的字段并获取数据。
        """
        # 市场过滤：只响应 HK 市场
        if market != "HK":
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
            elif category in ["indicators", "hk_indicators"]:
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
            df = provider.fetch_market(symbol, request_market, end_year=end_year, years=years)
            if df is not None and not df.empty:
                dfs.append(df)

        # 合并数据
        if not dfs:
            return None

        return self._merge_dfs(dfs)

    def _merge_dfs(self, dfs: list[pd.DataFrame]) -> pd.DataFrame | None:
        """合并多个 DataFrame
        
        策略：
        1. 保留第一个 DataFrame 的所有行（通常是 financial 数据，年份最全）
        2. 对于重复列，填充第一个 DataFrame 中的空值（使用其他 DataFrame 的非空值）
        3. 对于新列，直接添加
        """
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

            for col in df_to_merge.columns:
                if col == fiscal_year:
                    continue
                
                if col not in result.columns:
                    # 新列：左连接添加
                    result = result.merge(
                        df_to_merge[[col]],
                        left_index=True,
                        right_index=True,
                        how="left"
                    )
                else:
                    # 重复列：用 df_to_merge 的非空值填充 result 的空值
                    result[col] = result[col].fillna(df_to_merge[col])

        return result


# Plugin instance for pluggy registration
plugin = ProviderHKPlugin()
