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
    ) -> dict[str, dict[int, Any]] | None:
        """Fetch financial statement data"""
        provider = _get_provider()
        df = provider.fetch_financials(symbol, fields, end_year, years)
        if df is None or df.empty:
            return None

        # 转换为 {field: {year: value}} 格式
        return _df_to_dict(df, fields)

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
        df = provider.fetch_indicators(symbol, fields, end_year, years)
        if df is None or df.empty:
            return None

        return _df_to_dict(df, fields)

    @vi_hookimpl
    def vi_fetch_market(
        self,
        symbol: str,
        fields: set[str],
    ) -> dict[str, Any]:
        """Fetch market data"""
        provider = _get_provider()
        df = provider.fetch_market(symbol, fields)
        if df is None or df.empty:
            return {}

        # 返回最新一条数据
        row = df.iloc[0]
        result = {}
        for col in fields:
            if col in df.columns:
                value = row.get(col)
                if value is not None and not pd.isna(value):
                    result[col] = value
        return result


def _df_to_dict(df: pd.DataFrame, fields: set[str]) -> dict[str, dict[int, Any]]:
    """Convert DataFrame to {field: {year: value}}"""
    if df.empty:
        return {}

    result: dict[str, dict[int, Any]] = {}
    date_col = "year" if "year" in df.columns else df.columns[0]

    for col in fields:
        if col not in df.columns:
            continue
        result[col] = {}
        for _, row in df.iterrows():
            date_val = row.get(date_col)
            if date_val is None or pd.isna(date_val):
                continue
            year = int(date_val) if pd.api.types.is_integer_dtype(type(date_val)) else pd.to_datetime(str(date_val)).year
            value = row.get(col)
            if value is not None and not pd.isna(value):
                result[col][year] = value

    return result if result else None


# Plugin instance for pluggy registration
plugin = ProviderHKPlugin()
