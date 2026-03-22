"""US Stock Provider Implementation

从 AKShare API 获取美股市场数据。

继承 BaseDataProvider，自动获得：
- 字段映射（_apply_mapping）
- 数据去重（默认按日期）
- 模板方法（fetch_financials, fetch_indicators, fetch_market）
"""
from __future__ import annotations

from typing import Any

import akshare as ak
import pandas as pd

from vi_core import BaseDataProvider
from vi_fields_extension import StandardFields


class USProvider(BaseDataProvider):
    """AKShare data provider for US stock market"""

    MARKET_CODE = "US"

    # 字段映射: AKShare API 字段名 -> 系统标准字段名
    # 美股数据暂时只支持历史交易数据，其他字段待扩展
    FIELD_MAPPINGS: dict[str, dict[str, str]] = {
        "daily": {
            "open": StandardFields.open,
            "high": StandardFields.high,
            "low": StandardFields.low,
            "close": StandardFields.close,
            "volume": StandardFields.volume,
        },
    }

    # ========================================================================
    # BaseDataProvider 抽象方法实现
    # ========================================================================

    def _normalize_symbol(self, symbol: str) -> str:
        """标准化美股代码
        
        美股代码通常已经是标准格式（如 AAPL, GOOGL, MSFT），
        直接返回。
        """
        return symbol.upper()

    def _get_date_column(self) -> str:
        """US 使用 date 列作为日期列"""
        return "date"

    def _fetch_all_financials(
        self,
        symbol: str,
        start_year: int,
        end_year: int,
        fields: set[str],
    ) -> pd.DataFrame | None:
        """获取财务报表数据
        
        美股暂时不支持财务报表获取。
        """
        return None

    def _fetch_indicators_impl(
        self,
        symbol: str,
        start_year: int,
        end_year: int,
    ) -> pd.DataFrame | None:
        """获取财务指标数据
        
        美股暂时不支持财务指标获取。
        """
        return None

    def _fetch_market_impl(self, symbol: str) -> pd.DataFrame | None:
        """获取市场数据
        
        美股暂时不支持市场数据获取。
        """
        return None

    def _fetch_historical_impl(
        self,
        symbol: str,
        start_date: str | None,
        end_date: str | None,
        adjust: str,
    ) -> pd.DataFrame | None:
        """获取美股历史交易数据
        
        使用 AKShare stock_us_daily 接口获取日线数据。
        
        Args:
            symbol: 标准化后的股票代码 (如 AAPL, GOOGL)
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            adjust: 复权方式
                - "": 不复权
                - "qfq": 前复权 (美股主要使用前复权)
            
        Returns:
            DataFrame with columns: date, open, high, low, close, volume
        """
        try:
            df = ak.stock_us_daily(symbol=symbol, adjust=adjust)
            if df is None or df.empty:
                return None
            
            # AKShare 返回列名: date, open, high, low, close, volume
            # 确保列名存在
            expected_cols = ["date", "open", "high", "low", "close", "volume"]
            if not all(col in df.columns for col in expected_cols):
                return None
            
            # 按日期排序（升序）
            df = df.sort_values("date", ascending=True)
            
            return df
        except Exception:
            return None

    # ========================================================================
    # 辅助方法
    # ========================================================================

    def get_us_stock_list(self) -> pd.DataFrame:
        """获取美股股票列表
        
        Returns:
            包含美股股票信息的 DataFrame
        """
        try:
            return ak.stock_us_spot()
        except Exception:
            return pd.DataFrame()

    def get_us_stock_info(self, symbol: str) -> pd.DataFrame:
        """获取美股股票基本信息
        
        Args:
            symbol: 股票代码
            
        Returns:
            股票信息 DataFrame
        """
        try:
            return ak.stock_individual_info_us(symbol=symbol)
        except Exception:
            return pd.DataFrame()
