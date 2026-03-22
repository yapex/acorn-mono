"""Tushare Provider Implementation

从 Tushare API 获取 A 股市场数据。

继承 BaseDataProvider，自动获得：
- 字段映射（_apply_mapping）
- 数据去重（_deduplicate）
- 模板方法（fetch_financials, fetch_indicators, fetch_market）
"""
from __future__ import annotations

import os
from typing import Any

import pandas as pd
import tushare as ts

from vi_core import BaseDataProvider
from vi_core.base_provider import get_ttl_until_april_next_year
from vi_fields_extension import StandardFields


class TushareProvider(BaseDataProvider):
    """Tushare data provider for A 股 market"""

    MARKET_CODE = "A"

    # 字段映射: Tushare API 原始字段名 -> 系统标准字段名
    FIELD_MAPPINGS: dict[str, dict[str, str]] = {
        "balance_sheet": {
            "total_assets": StandardFields.total_assets,
            "total_liab": StandardFields.total_liabilities,
            "total_hldr_eqy_exc_min_int": StandardFields.total_equity,
            "total_cur_liab": StandardFields.current_liabilities,
            "money_cap": StandardFields.cash_and_equivalents,
            "inventories": StandardFields.inventory,
            "accounts_receiv": StandardFields.accounts_receivable,
            "fix_assets": StandardFields.fixed_assets,
            "total_cur_assets": StandardFields.current_assets,
            "accounts_pay": StandardFields.accounts_payable,
            "prepayment": StandardFields.prepayment,
            "contract_assets": StandardFields.contract_assets,
            "contract_liab": StandardFields.contract_liab,
            "adv_receipts": StandardFields.adv_receipts,
            "total_share": StandardFields.total_shares,
            "goodwill": StandardFields.goodwill,
            "intan_assets": StandardFields.intangible_assets,
            "lt_eqt_invest": StandardFields.long_term_investment,
            "cip": StandardFields.construction_in_progress,
            "st_borr": StandardFields.short_term_borrowings,
            "lt_borr": StandardFields.long_term_debt,
            "non_cur_liab_due_1y": StandardFields.non_current_liabilities_due_1y,
            "bond_payable": StandardFields.bond_payable,
            "oth_receiv": StandardFields.other_receivables,
        },
        "income_statement": {
            "total_revenue": StandardFields.total_revenue,
            "revenue": StandardFields.main_business_income,
            "n_income": StandardFields.net_profit,
            "operate_profit": StandardFields.operating_profit,
            "oper_cost": StandardFields.operating_cost,
            "n_income_attr_p": StandardFields.parent_net_profit,
            "int_exp": StandardFields.interest_expense,
            "int_income": StandardFields.interest_income,
            "non_oper_income": StandardFields.non_operating_income,
            "invest_income": StandardFields.investment_income,
            "fv_value_chg_gain": StandardFields.fair_value_change,
        },
        "cash_flow": {
            "n_cashflow_act": StandardFields.operating_cash_flow,
            "n_cashflow_inv_act": StandardFields.investing_cash_flow,
            "n_cash_flows_fnc_act": StandardFields.financing_cash_flow,
            "c_pay_acq_const_fiolta": StandardFields.capital_expenditure,
        },
        "indicators": {
            "roe": StandardFields.roe,
            "roa": StandardFields.roa,
            "grossprofit_margin": StandardFields.gross_margin,
            "netprofit_margin": StandardFields.net_profit_margin,
            "current_ratio": StandardFields.current_ratio,
            "quick_ratio": StandardFields.quick_ratio,
            "debt_to_assets": StandardFields.debt_ratio,
            "assets_turn": StandardFields.asset_turnover,
            "ar_turn": StandardFields.receivable_turnover,
            "roic": StandardFields.roic,
            "eps": StandardFields.basic_eps,
            "dt_eps": StandardFields.diluted_eps,
            "bps": StandardFields.book_value_per_share,
            "cash_ratio": StandardFields.cash_ratio,
            "ocf_to_debt": StandardFields.ocf_to_debt,
            "interestdebt": StandardFields.interest_bearing_debt,
            "ebitda": StandardFields.ebitda,
            "currentdebt_to_debt": StandardFields.currentdebt_to_debt,
            "op_of_gr": StandardFields.operating_profit_margin,
            "tr_yoy": StandardFields.revenue_yoy,
            "netprofit_yoy": StandardFields.net_profit_yoy,
            "netdebt": StandardFields.net_debt,
            "ebit": StandardFields.ebit,
            "fcff": StandardFields.free_cash_flow_to_firm,
            "fcfe": StandardFields.free_cash_flow_to_equity,
            "ocf_to_shortdebt": StandardFields.ocf_to_short_debt,
            "debt_to_eqt": StandardFields.debt_to_equity,
            "longdeb_to_debt": StandardFields.long_term_debt_ratio,
            "ca_to_assets": StandardFields.current_assets_ratio,
            "saleexp_to_gr": StandardFields.selling_expense_ratio,
            "adminexp_of_gr": StandardFields.admin_expense_ratio,
            "finaexp_of_gr": StandardFields.finance_expense_ratio,
            "assets_yoy": StandardFields.total_assets_yoy,
            "eqt_yoy": StandardFields.equity_yoy,
            "ocf_yoy": StandardFields.operating_cash_flow_yoy,
        },
        "market": {
            "total_mv": StandardFields.market_cap,
            "circ_mv": StandardFields.circ_market_cap,
            "float_share": StandardFields.circ_shares,
            "pe_ttm": StandardFields.pe_ratio,
            "pb": StandardFields.pb_ratio,
            "total_share": StandardFields.total_shares,
        },
        "daily": {
            "close": StandardFields.close,
            "open": StandardFields.open,
            "high": StandardFields.high,
            "low": StandardFields.low,
            "vol": StandardFields.volume,
        },
    }

    # ========================================================================
    # 初始化
    # ========================================================================

    def __init__(self, token: str | None = None, cache: Any = None):
        """Initialize Tushare provider

        Args:
            token: Tushare API token (optional, can use TUSHARE_TOKEN env var)
            cache: SmartCache instance for caching (optional)
        """
        self._token = token or os.environ.get("TUSHARE_TOKEN", "")
        self._api: Any = None
        super().__init__(cache=cache)

    def _init_provider(self) -> None:
        """Lazy init Tushare API"""
        pass

    @property
    def api(self):
        """Lazy init Tushare API (instance-level singleton)"""
        if self._api is None:
            if self._token:
                ts.set_token(self._token)
            self._api = ts.pro_api()
        return self._api

    # ========================================================================
    # BaseDataProvider 抽象方法实现
    # ========================================================================

    def _normalize_symbol(self, symbol: str) -> str:
        """Convert 6-digit stock code to ts_code format"""
        if "." in symbol:
            return symbol

        if len(symbol) == 6 and symbol.isdigit():
            if symbol.startswith(("0", "3")):
                return f"{symbol}.SZ"
            elif symbol.startswith("6"):
                return f"{symbol}.SH"

        return symbol

    def _get_date_column(self) -> str:
        """A 股使用 end_date 作为日期列"""
        return "end_date"

    def _get_financial_ttl(self, end_year: int) -> int:
        """A 股财务数据缓存到次年4月底
        
        A股年报一般在4月底前发布，所以缓存到次年4月底即可。
        """
        return get_ttl_until_april_next_year(end_year)

    def _fetch_all_financials(
        self,
        symbol: str,
        start_year: int,
        end_year: int,
        fields: set[str],
    ) -> pd.DataFrame | None:
        """获取所有财务报表数据并合并"""
        start_date = f"{start_year}0101"
        end_date = f"{end_year}1231"

        dfs = []

        # 资产负债表
        try:
            df = self.api.balancesheet(
                ts_code=symbol,
                start_date=start_date,
                end_date=end_date,
            )
            if df is not None and not df.empty:
                df = self._filter_annual_reports(df)
                dfs.append(df)
        except Exception:
            pass

        # 利润表
        try:
            df = self.api.income(
                ts_code=symbol,
                start_date=start_date,
                end_date=end_date,
            )
            if df is not None and not df.empty:
                df = self._filter_annual_reports(df)
                dfs.append(df)
        except Exception:
            pass

        # 现金流量表
        try:
            df = self.api.cashflow(
                ts_code=symbol,
                start_date=start_date,
                end_date=end_date,
            )
            if df is not None and not df.empty:
                df = self._filter_annual_reports(df)
                dfs.append(df)
        except Exception:
            pass

        if not dfs:
            return None

        # 按 end_date 合并
        result = dfs[0]
        for df in dfs[1:]:
            result = result.merge(df, on="end_date", how="outer", suffixes=("", "_dup"))
            # 移除重复列
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
            df = self.api.fina_indicator(
                ts_code=symbol,
                start_date=f"{start_year}0101",
                end_date=f"{end_year}1231",
            )
            if df is not None and not df.empty:
                df = self._filter_annual_reports(df)
                return df
        except Exception:
            pass
        return None

    def _fetch_market_impl(self, symbol: str) -> pd.DataFrame | None:
        """获取市场数据"""
        try:
            # 获取 daily_basic
            df = self.api.daily_basic(ts_code=symbol)
            if df is None or df.empty:
                return None

            # 获取 daily（交易数据）
            try:
                df_daily = self.api.daily(ts_code=symbol)
                if df_daily is not None and not df_daily.empty:
                    # 合并
                    df = df.merge(df_daily, on="trade_date", how="left", suffixes=("", "_daily"))
            except Exception:
                pass

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
        """获取 A 股历史交易数据
        
        使用 Tushare pro_bar 接口获取日线数据。
        
        Args:
            symbol: 标准化后的股票代码 (如 600519.SH)
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            adjust: 复权方式 ("", "qfq", "hfq")
            
        Returns:
            DataFrame with columns: date, open, high, low, close, volume
        """
        try:
            # 转换日期格式：YYYY-MM-DD -> YYYYMMDD
            start_str = start_date.replace("-", "") if start_date else None
            end_str = end_date.replace("-", "") if end_date else None
            
            # 获取数据
            adj_param = adjust if adjust else None  # Tushare: None 表示不复权
            df = ts.pro_bar(
                ts_code=symbol,
                start_date=start_str,
                end_date=end_str,
                adj=adj_param,
                freq="D",
            )
            
            if df is None or df.empty:
                return None
            
            # 重命名列：trade_date -> date, vol -> volume
            df = df.rename(columns={
                "trade_date": "date",
                "vol": "volume",
            })
            
            # 按日期排序（降序 -> 升序）
            df = df.sort_values("date", ascending=True)
            
            return df
        except Exception:
            return None

    # ========================================================================
    # A 股特定逻辑
    # ========================================================================

    def _filter_annual_reports(self, df: pd.DataFrame) -> pd.DataFrame:
        """Filter to keep only annual reports (end_date ends with 1231)"""
        if df.empty or "end_date" not in df.columns:
            return df

        result = df.copy()
        mask = result["end_date"].astype(str).str.endswith("1231")
        result = result.loc[mask]

        return result

    def _deduplicate(self, df: pd.DataFrame) -> pd.DataFrame:
        """A 股数据去重
        
        按 update_flag 排序，保留最新记录（每个日期只保留一条）。
        """
        if df is None or df.empty:
            return df

        date_col = self._get_date_column()
        if date_col not in df.columns:
            return df

        # 按 update_flag 和日期排序，保留最新
        if "update_flag" in df.columns:
            df = df.sort_values([date_col, "update_flag"], ascending=[False, False])
            df = df.drop_duplicates(subset=[date_col], keep="last")  # update_flag 最新在最后
        else:
            df = df.sort_values(date_col, ascending=False)
            df = df.drop_duplicates(subset=[date_col], keep="first")

        return df
