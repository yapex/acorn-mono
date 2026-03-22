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

    # 中文科目名 -> 系统标准字段名 映射（用于财务报表）
    # AKShare 美股财务报表返回中文字段名
    CN_TO_STANDARD_FIELDS: dict[str, str] = {
        # 资产负债表
        "现金及现金等价物": StandardFields.cash_and_equivalents,
        "应收账款": StandardFields.accounts_receivable,
        "存货": StandardFields.inventory,
        "流动资产合计": StandardFields.current_assets,
        "总资产": StandardFields.total_assets,
        "应付账款": StandardFields.accounts_payable,
        "流动负债合计": StandardFields.current_liabilities,
        "总负债": StandardFields.total_liabilities,
        "总权益": StandardFields.total_equity,
        "非流动资产合计": StandardFields.non_current_assets,
        "非流动负债合计": StandardFields.non_current_liabilities,
        "固定资产": StandardFields.fixed_assets,
        "无形资产": StandardFields.intangible_assets,
        "商誉": StandardFields.goodwill,
        "长期投资": StandardFields.long_term_investment,
        "长期负债": StandardFields.long_term_debt,
        "短期借款": StandardFields.short_term_debt,
        # 利润表
        "主营收入": StandardFields.main_business_income,
        "营业收入": StandardFields.total_revenue,
        "毛利": StandardFields.gross_profit,
        "营业利润": StandardFields.operating_profit,
        "净利润": StandardFields.net_profit,
        "归属于普通股股东净利润": StandardFields.parent_net_profit,
        "归属于母公司股东净利润": StandardFields.parent_net_profit,
        "基本每股收益-普通股": StandardFields.basic_eps,
        "摊薄每股收益-普通股": StandardFields.diluted_eps,
        "营业成本": StandardFields.operating_cost,
        # 现金流量表
        "经营活动产生的现金流量净额": StandardFields.operating_cash_flow,
        "购买固定资产": StandardFields.capital_expenditure,
        "购建无形资产及其他资产": StandardFields.capital_expenditure_intangible,
    }

    # 字段映射: AKShare API 字段名 -> 系统标准字段名
    FIELD_MAPPINGS: dict[str, dict[str, str]] = {
        "balance_sheet": {
            "现金及现金等价物": StandardFields.cash_and_equivalents,
            "应收账款": StandardFields.accounts_receivable,
            "存货": StandardFields.inventory,
            "流动资产合计": StandardFields.current_assets,
            "总资产": StandardFields.total_assets,
            "应付账款": StandardFields.accounts_payable,
            "流动负债合计": StandardFields.current_liabilities,
            "总负债": StandardFields.total_liabilities,
            "总权益": StandardFields.total_equity,
            "非流动资产合计": StandardFields.non_current_assets,
            "非流动负债合计": StandardFields.non_current_liabilities,
            "固定资产": StandardFields.fixed_assets,
            "无形资产": StandardFields.intangible_assets,
            "商誉": StandardFields.goodwill,
            "长期投资": StandardFields.long_term_investment,
            "长期负债": StandardFields.long_term_debt,
            "短期借款": StandardFields.short_term_debt,
        },
        "income_statement": {
            "主营收入": StandardFields.main_business_income,
            "营业收入": StandardFields.total_revenue,
            "毛利": StandardFields.gross_profit,
            "营业利润": StandardFields.operating_profit,
            "净利润": StandardFields.net_profit,
            "归属于普通股股东净利润": StandardFields.parent_net_profit,
            "归属于母公司股东净利润": StandardFields.parent_net_profit,
            "基本每股收益-普通股": StandardFields.basic_eps,
            "摊薄每股收益-普通股": StandardFields.diluted_eps,
            "营业成本": StandardFields.operating_cost,
        },
        "cash_flow": {
            "经营活动产生的现金流量净额": StandardFields.operating_cash_flow,
            "购买固定资产": StandardFields.capital_expenditure,
            "购建无形资产及其他资产": StandardFields.capital_expenditure_intangible,
        },
        "indicators": {
            "ROE_AVG": StandardFields.roe,
            "ROA": StandardFields.roa,
            "GROSS_PROFIT_RATIO": StandardFields.gross_margin,
            "NET_PROFIT_RATIO": StandardFields.net_profit_margin,
            "CURRENT_RATIO": StandardFields.current_ratio,
            "SPEED_RATIO": StandardFields.quick_ratio,
            "DEBT_ASSET_RATIO": StandardFields.debt_ratio,
            "BASIC_EPS": StandardFields.basic_eps,
            "DILUTED_EPS": StandardFields.diluted_eps,
        },
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
        直接返回大写形式。
        """
        return symbol.upper()

    def _get_date_column(self) -> str:
        """US 使用 REPORT_DATE 作为日期列"""
        return "REPORT_DATE"

    def _fetch_all_financials(
        self,
        symbol: str,
        start_year: int,
        end_year: int,
        fields: set[str],
    ) -> pd.DataFrame | None:
        """获取财务报表数据
        
        从东方财富获取美股三大报表，合并为一个 DataFrame。
        
        Args:
            symbol: 股票代码
            start_year: 开始年份
            end_year: 结束年份
            fields: 需要的字段集合
            
        Returns:
            原始 DataFrame（未映射字段）
        """
        dfs = []

        # 资产负债表
        try:
            df = ak.stock_financial_us_report_em(
                stock=symbol, symbol="资产负债表", indicator="年报"
            )
            if df is not None and not df.empty:
                df = self._pivot_financial_df(df)
                dfs.append(df)
        except Exception:
            pass

        # 利润表
        try:
            df = ak.stock_financial_us_report_em(
                stock=symbol, symbol="综合损益表", indicator="年报"
            )
            if df is not None and not df.empty:
                df = self._pivot_financial_df(df)
                dfs.append(df)
        except Exception:
            pass

        # 现金流量表
        try:
            df = ak.stock_financial_us_report_em(
                stock=symbol, symbol="现金流量表", indicator="年报"
            )
            if df is not None and not df.empty:
                df = self._pivot_financial_df(df)
                dfs.append(df)
        except Exception:
            pass

        if not dfs:
            return None

        # 按 REPORT_DATE 合并
        result = dfs[0]
        for df in dfs[1:]:
            result = result.merge(df, on="REPORT_DATE", how="outer", suffixes=("", "_dup"))
            dup_cols = [c for c in result.columns if c.endswith("_dup")]
            result = result.drop(columns=dup_cols)

        return result

    def _pivot_financial_df(self, df: pd.DataFrame) -> pd.DataFrame:
        """将长表格式的财务报表转换为宽表
        
        AKShare 返回的财务报表是长表格式：每行一个科目。
        需要 pivot 成宽表：每列一个科目，每行一个报告期。
        """
        if df.empty:
            return df

        if "ITEM_NAME" not in df.columns or "AMOUNT" not in df.columns:
            return df

        # pivot
        try:
            wide_df = df.pivot_table(
                index="REPORT_DATE",
                columns="ITEM_NAME",
                values="AMOUNT",
                aggfunc="first",
            )
            wide_df = wide_df.reset_index()
            wide_df["REPORT_DATE"] = pd.to_datetime(wide_df["REPORT_DATE"])
            return wide_df
        except Exception:
            return df

    def _fetch_indicators_impl(
        self,
        symbol: str,
        start_year: int,
        end_year: int,
    ) -> pd.DataFrame | None:
        """获取财务指标数据
        
        使用东方财富美股财务指标接口。
        
        Args:
            symbol: 标准化后的股票代码
            start_year: 开始年份
            end_year: 结束年份
            
        Returns:
            原始 DataFrame
        """
        try:
            df = ak.stock_financial_us_analysis_indicator_em(
                symbol=symbol, indicator="年报"
            )
            if df is None or df.empty:
                return None

            # 只保留需要的列
            cols_to_keep = ["REPORT_DATE"] + [
                c for c in df.columns if c in [
                    "OPERATE_INCOME", "PARENT_HOLDER_NETPROFIT", "BASIC_EPS",
                    "DILUTED_EPS", "GROSS_PROFIT", "GROSS_PROFIT_RATIO",
                    "NET_PROFIT_RATIO", "ROE_AVG", "ROA", "CURRENT_RATIO",
                    "SPEED_RATIO", "DEBT_ASSET_RATIO", "EQUITY_RATIO",
                    "TOTAL_ASSETS_TR", "ACCOUNTS_RECE_TR", "INVENTORY_TR",
                ]
            ]
            cols_to_keep = [c for c in cols_to_keep if c in df.columns]
            
            df = df[cols_to_keep].copy()
            df["REPORT_DATE"] = pd.to_datetime(df["REPORT_DATE"])
            
            return df
        except Exception:
            return None

    def _fetch_market_impl(self, symbol: str) -> pd.DataFrame | None:
        """获取市场数据
        
        美股市场数据暂时不支持。
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
                - "hfq": 后复权（美股不支持，自动转为 qfq）
            
        Returns:
            DataFrame with columns: date, open, high, low, close, volume
        """
        try:
            # AKShare 美股接口只支持 "" 和 "qfq"，不支持 "hfq"
            if adjust == "hfq":
                adjust = "qfq"
            
            df = ak.stock_us_daily(symbol=symbol, adjust=adjust)
            if df is None or df.empty:
                return None
            
            # AKShare 返回列名: date, open, high, low, close, volume
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
