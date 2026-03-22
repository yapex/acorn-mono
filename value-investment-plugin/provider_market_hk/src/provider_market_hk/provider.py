"""HK Provider Implementation

从 AKShare API 获取港股市场数据。

继承 BaseDataProvider，自动获得：
- 字段映射（_apply_mapping）
- 数据去重（默认按日期）
- 模板方法（fetch_financials, fetch_indicators, fetch_market）
"""
from __future__ import annotations

import warnings
from typing import Any

import akshare as ak
import pandas as pd

from vi_core import BaseDataProvider
from vi_fields_extension import StandardFields


class HKProvider(BaseDataProvider):
    """AKShare data provider for HK market"""

    MARKET_CODE = "HK"

    # 字段映射: AKShare API 中文字段名 -> 系统标准字段名
    FIELD_MAPPINGS: dict[str, dict[str, str]] = {
        "balance_sheet": {
            # 资产类
            "总资产": StandardFields.total_assets,
            "流动资产合计": StandardFields.current_assets,
            "非流动资产合计": StandardFields.non_current_assets,
            "现金及等价物": StandardFields.cash_and_equivalents,
            "应收帐款": StandardFields.accounts_receivable,
            "存货": StandardFields.inventory,
            "固定资产": StandardFields.fixed_assets,
            "物业厂房及设备": StandardFields.fixed_assets,
            "无形资产": StandardFields.intangible_assets,
            "在建工程": StandardFields.construction_in_progress,
            "预付款项": StandardFields.prepayment,
            "合同资产": StandardFields.contract_assets,
            "联营公司权益": StandardFields.investment_in_associates,
            "合营公司权益": StandardFields.investment_in_joint_ventures,
            # 负债类
            "总负债": StandardFields.total_liabilities,
            "流动负债合计": StandardFields.current_liabilities,
            "非流动负债合计": StandardFields.non_current_liabilities,
            "应付帐款": StandardFields.accounts_payable,
            "短期贷款": StandardFields.short_term_debt,
            "长期贷款": StandardFields.long_term_debt,
            "合同负债": StandardFields.contract_liab,
            "预收款项": StandardFields.adv_receipts,
            # 权益类
            "权益总额": StandardFields.total_equity,
            "股东权益": StandardFields.shareholders_equity,
            "股本": StandardFields.share_capital,
            "股本溢价": StandardFields.share_premium,
            "保留溢利(累计亏损)": StandardFields.retained_earnings,
        },
        "income_statement": {
            # 收益
            "收益": StandardFields.total_revenue,
            "营业额": StandardFields.total_revenue,
            # 利润
            "毛利": StandardFields.gross_profit,
            "经营溢利": StandardFields.operating_profit,
            "除税前溢利": StandardFields.profit_before_tax,
            "除税后溢利": StandardFields.profit_after_tax,
            "股东应占溢利": StandardFields.parent_net_profit,
            # 费用
            "营业成本": StandardFields.operating_cost,
            "行政开支": StandardFields.administrative_expenses,
            "销售及分销费用": StandardFields.selling_distribution_expenses,
            "融资成本": StandardFields.finance_cost,
            # 其他
            "利息收入": StandardFields.interest_income,
            "折旧及摊销": StandardFields.depreciation_amortization,
        },
        "cash_flow": {
            "经营业务现金净额": StandardFields.operating_cash_flow,
            "投资业务现金净额": StandardFields.investing_cash_flow,
            "融资业务现金净额": StandardFields.financing_cash_flow,
            "购建固定资产": StandardFields.capital_expenditure,
            "购建无形资产及其他资产": StandardFields.capital_expenditure_intangible,
            "已付利息(经营)": StandardFields.interest_paid_operating,
            "已付利息(融资)": StandardFields.interest_paid_financing,
            "已付税项": StandardFields.taxes_paid,
            "已收利息(投资)": StandardFields.interest_received,
            "已收股息(投资)": StandardFields.dividend_received,
            "期初现金": StandardFields.cash_begin,
            "期末现金": StandardFields.cash_end,
            "现金净额": StandardFields.net_cash_change,
        },
        "indicators": {
            # 收益类
            "营业总收入": StandardFields.total_revenue,
            "净利润": StandardFields.net_profit,
            # 每股数据
            "基本每股收益(元)": StandardFields.basic_eps,
            "每股净资产(元)": StandardFields.book_value_per_share,
            "每股经营现金流(元)": StandardFields.operating_cash_flow_per_share,
            "每股股息TTM(港元)": StandardFields.hk_dividend_per_share,
            # 比率
            "股东权益回报率(%)": StandardFields.roe,
            "销售净利率(%)": StandardFields.net_profit_margin,
            "总资产回报率(%)": StandardFields.roa,
            "股息率TTM(%)": StandardFields.hk_dividend_yield_ttm,
            "派息比率(%)": StandardFields.hk_dividend_payout_ratio,
            # 增长
            "营业总收入滚动环比增长(%)": StandardFields.hk_total_revenue_growth_qoq,
            "净利润滚动环比增长(%)": StandardFields.hk_net_profit_growth_qoq,
        },
        "market": {
            # 市值
            "总市值(港元)": StandardFields.hk_market_cap,
            "港股市值(港元)": StandardFields.hk_market_cap,
            # 估值
            "市盈率": StandardFields.pe_ratio,
            "市净率": StandardFields.pb_ratio,
            # 股息
            "股息率TTM(%)": StandardFields.hk_dividend_yield_ttm,
            "派息比率(%)": StandardFields.hk_dividend_payout_ratio,
            "每股股息TTM(港元)": StandardFields.hk_dividend_per_share,
        },
    }

    # ========================================================================
    # BaseDataProvider 抽象方法实现
    # ========================================================================

    def _normalize_symbol(self, symbol: str) -> str:
        """标准化港股代码为 5 位数字格式"""
        if not symbol:
            return symbol
        digits = "".join(c for c in symbol if c.isdigit())
        if len(digits) < 5:
            digits = digits.zfill(5)
        return digits

    def _get_date_column(self) -> str:
        """HK 使用 year 列作为日期列"""
        return "year"

    def _fetch_all_financials(
        self,
        symbol: str,
        start_year: int,
        end_year: int,
        fields: set[str],
    ) -> pd.DataFrame | None:
        """获取所有财务报表数据并合并"""
        dfs = []

        # 资产负债表
        try:
            df = self._fetch_balance_sheet(symbol)
            if df is not None and not df.empty:
                dfs.append(df)
        except Exception:
            pass

        # 利润表
        try:
            df = self._fetch_income_statement(symbol)
            if df is not None and not df.empty:
                dfs.append(df)
        except Exception:
            pass

        # 现金流量表
        try:
            df = self._fetch_cash_flow(symbol)
            if df is not None and not df.empty:
                dfs.append(df)
        except Exception:
            pass

        if not dfs:
            return None

        # 按 year 合并
        result = dfs[0]
        for df in dfs[1:]:
            result = result.merge(df, on="year", how="outer", suffixes=("", "_dup"))
            dup_cols = [c for c in result.columns if c.endswith("_dup")]
            result = result.drop(columns=dup_cols)

        return result

    def _fetch_indicators_impl(
        self,
        symbol: str,
        start_year: int,
        end_year: int,
    ) -> pd.DataFrame | None:
        """获取财务指标数据"""
        try:
            df = ak.stock_hk_financial_indicator_em(symbol=symbol)
            if df is None or df.empty:
                return None
            return df
        except Exception:
            return None

    def _fetch_market_impl(self, symbol: str) -> pd.DataFrame | None:
        """获取市场数据"""
        try:
            df = ak.stock_hk_financial_indicator_em(symbol=symbol)
            return df
        except Exception:
            return None

    def _fetch_historical_impl(
        self,
        symbol: str,
        start_date: str | None,
        end_date: str | None,
        adjust: str,
    ) -> pd.DataFrame | None:
        """获取港股历史交易数据
        
        使用 AKShare stock_hk_daily 接口获取日线数据。
        
        Args:
            symbol: 标准化后的股票代码 (5位数字)
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            adjust: 复权方式
                - "": 不复权
                - "qfq": 前复权
                - "hfq": 后复权
            
        Returns:
            DataFrame with columns: date, open, high, low, close, volume
        """
        try:
            df = ak.stock_hk_daily(symbol=symbol, adjust=adjust)
            if df is None or df.empty:
                return None
            
            # AKShare 返回列名: date, open, high, low, close, volume, amount
            # 确认列名存在
            expected_cols = ["date", "open", "high", "low", "close", "volume"]
            if not all(col in df.columns for col in expected_cols):
                # 尝试映射中文列名
                col_mapping = {
                    "日期": "date",
                    "开盘": "open",
                    "最高": "high",
                    "最低": "low",
                    "收盘": "close",
                    "成交量": "volume",
                    "成交额": "amount",
                }
                df = df.rename(columns=col_mapping)
            
            # 按日期排序（升序）
            df = df.sort_values("date", ascending=True)
            
            return df
        except Exception:
            return None

    # ========================================================================

    def _fetch_balance_sheet(self, symbol: str) -> pd.DataFrame | None:
        """获取资产负债表"""
        try:
            df = ak.stock_financial_hk_report_em(
                stock=symbol, symbol="资产负债表", indicator="年度"
            )
            if df is None or df.empty:
                return None
            return self._transform_financial_df(df)
        except Exception:
            return None

    def _fetch_income_statement(self, symbol: str) -> pd.DataFrame | None:
        """获取利润表"""
        try:
            df = ak.stock_financial_hk_report_em(
                stock=symbol, symbol="利润表", indicator="年度"
            )
            if df is None or df.empty:
                return None
            return self._transform_financial_df(df)
        except Exception:
            return None

    def _fetch_cash_flow(self, symbol: str) -> pd.DataFrame | None:
        """获取现金流量表"""
        try:
            df = ak.stock_financial_hk_report_em(
                stock=symbol, symbol="现金流量表", indicator="年度"
            )
            if df is None or df.empty:
                return None
            return self._transform_financial_df(df)
        except Exception:
            return None

    def _transform_financial_df(self, df: pd.DataFrame) -> pd.DataFrame:
        """转换长表为宽表"""
        if df.empty:
            return df

        item_col = None
        for col in ["STD_ITEM_NAME", "ITEM_NAME"]:
            if col in df.columns:
                item_col = col
                break

        if item_col is None or "AMOUNT" not in df.columns:
            return df

        if "REPORT_DATE" in df.columns:
            df = df.copy()
            df["year"] = pd.to_datetime(df["REPORT_DATE"]).dt.year

        try:
            wide_df = df.pivot_table(
                index="year",
                columns=item_col,
                values="AMOUNT",
                aggfunc="first",
            )
            return wide_df.reset_index()
        except Exception:
            return df

    def get_stock_info(self, symbol: str) -> pd.DataFrame:
        """获取股票基本信息"""
        try:
            return ak.stock_hk_company_profile_em(symbol=symbol)
        except Exception:
            return pd.DataFrame()

    def get_historical_data(
        self,
        symbol: str,
        start_date: str | None = None,
        end_date: str | None = None,
        adjust: str = "",
    ) -> pd.DataFrame:
        """获取历史交易数据"""
        warnings.warn(
            "港股历史交易数据建议使用 yfinance。AKShare 的港股历史数据接口不够稳定。",
            DeprecationWarning,
            stacklevel=2,
        )
        try:
            df = ak.stock_hk_daily(symbol=symbol)
            return df.rename(
                columns={
                    "date": "日期",
                    "open": "开盘",
                    "close": "收盘",
                    "high": "最高",
                    "low": "最低",
                    "volume": "成交量",
                }
            )
        except Exception:
            return pd.DataFrame()
