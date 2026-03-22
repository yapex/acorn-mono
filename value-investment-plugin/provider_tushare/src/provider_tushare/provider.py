"""Tushare Provider Implementation

从 Tushare API 获取 A 股市场数据。

字段定义：
- FIELD_MAPPINGS: 定义 Tushare API 原始字段到系统标准字段的映射
- 使用 StandardFields 常量引用，避免硬编码字段名
- Provider 通过 vi_supported_fields 返回所有 FIELD_MAPPINGS 的值（即系统标准字段名）
"""
from __future__ import annotations

import os
from typing import Any

import pandas as pd

# Tushare API (lazy import)
_tushare: Any = None


def _get_tushare():
    """Lazy import tushare"""
    global _tushare
    if _tushare is None:
        import tushare as ts

        token = os.environ.get("TUSHARE_TOKEN", "")
        if token:
            ts.set_token(token)
        _tushare = ts.pro_api()
    return _tushare


# 使用标准字段常量引用
from vi_fields_extension import StandardFields


class TushareProvider:
    """Tushare data provider for A 股 market"""

    # 字段映射: Tushare API 原始字段名 -> 系统标准字段名
    # 使用 StandardFields 常量引用，当字段名改变时只需更新 StandardFields
    FIELD_MAPPINGS: dict[str, dict[str, str]] = {
        "balance_sheet": {
            # Tushare API 字段: 系统标准字段（常量引用）
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
    # 动态派生的字段集合（从 FIELD_MAPPINGS 计算）
    # ========================================================================

    # Provider 声称支持的所有系统标准字段（从映射表的值集合计算）
    @classmethod
    def get_supported_fields(cls) -> set[str]:
        """获取 Provider 支持的所有系统标准字段"""
        fields = set()
        for mapping_dict in cls.FIELD_MAPPINGS.values():
            fields.update(mapping_dict.values())
        return fields

    # 财务指标字段
    _INDICATOR_FIELDS: set[str] = set(FIELD_MAPPINGS.get("indicators", {}).values())

    # 市场数据字段
    _MARKET_FIELDS: set[str] = set(FIELD_MAPPINGS.get("market", {}).values())

    # 交易数据字段
    _TRADING_FIELDS: set[str] = set(FIELD_MAPPINGS.get("daily", {}).values())

    # 财务报表字段分类
    _BALANCE_FIELDS: set[str] = set(FIELD_MAPPINGS.get("balance_sheet", {}).values())
    _INCOME_FIELDS: set[str] = set(FIELD_MAPPINGS.get("income_statement", {}).values())
    _CASH_FIELDS: set[str] = set(FIELD_MAPPINGS.get("cash_flow", {}).values())

    def __init__(self, token: str | None = None):
        """Initialize Tushare provider

        Args:
            token: Tushare API token (optional, can use TUSHARE_TOKEN env var)
        """
        self._token = token or os.environ.get("TUSHARE_TOKEN", "")
        self._api: Any = None

    @property
    def api(self):
        """Lazy init Tushare API"""
        if self._api is None:
            import tushare as ts

            if self._token:
                ts.set_token(self._token)
            self._api = ts.pro_api()
        return self._api

    def _to_ts_code(self, stock_code: str) -> str:
        """Convert 6-digit stock code to ts_code format"""
        if "." in stock_code:
            return stock_code

        if len(stock_code) == 6 and stock_code.isdigit():
            if stock_code.startswith(("0", "3")):
                return f"{stock_code}.SZ"
            elif stock_code.startswith("6"):
                return f"{stock_code}.SH"

        return stock_code

    def _filter_annual_reports(self, df: pd.DataFrame, date_col: str = "end_date") -> pd.DataFrame:
        """Filter to keep only annual reports (end_date ends with 1231)"""
        if df.empty or date_col not in df.columns:
            return df

        result = df.copy()
        mask = result[date_col].astype(str).str.endswith("1231")
        result = result.loc[mask]

        # Keep latest by update_flag
        if "update_flag" in result.columns:
            result = result.sort_values(["update_flag"], ascending=False)
            result = result.drop_duplicates(subset=[date_col], keep="first")

        return result

    def _apply_mapping(self, df: pd.DataFrame, statement_type: str) -> pd.DataFrame:
        """Apply field mapping"""
        if df.empty:
            return df

        mapping = self.FIELD_MAPPINGS.get(statement_type, {})
        rename_map = {
            native: std for native, std in mapping.items() if native in df.columns
        }
        if rename_map:
            df = df.rename(columns=rename_map)
        return df

    def _fetch_balance_sheet(
        self, ts_code: str, start_year: int, end_year: int
    ) -> pd.DataFrame:
        """Fetch balance sheet data"""
        df = self.api.balancesheet(
            ts_code=ts_code,
            start_date=f"{start_year}0101",
            end_date=f"{end_year}1231",
        )
        if df is not None and not df.empty:
            df = self._filter_annual_reports(df)
            df = self._apply_mapping(df, "balance_sheet")
        return df if df is not None else pd.DataFrame()

    def _fetch_income_statement(
        self, ts_code: str, start_year: int, end_year: int
    ) -> pd.DataFrame:
        """Fetch income statement data"""
        df = self.api.income(
            ts_code=ts_code,
            start_date=f"{start_year}0101",
            end_date=f"{end_year}1231",
        )
        if df is not None and not df.empty:
            df = self._filter_annual_reports(df)
            df = self._apply_mapping(df, "income_statement")
        return df if df is not None else pd.DataFrame()

    def _fetch_cash_flow(
        self, ts_code: str, start_year: int, end_year: int
    ) -> pd.DataFrame:
        """Fetch cash flow data"""
        df = self.api.cashflow(
            ts_code=ts_code,
            start_date=f"{start_year}0101",
            end_date=f"{end_year}1231",
        )
        if df is not None and not df.empty:
            df = self._filter_annual_reports(df)
            df = self._apply_mapping(df, "cash_flow")
        return df if df is not None else pd.DataFrame()

    def _fetch_indicators(
        self, ts_code: str, start_year: int, end_year: int
    ) -> pd.DataFrame:
        """Fetch financial indicators"""
        df = self.api.fina_indicator(
            ts_code=ts_code,
            start_date=f"{start_year}0101",
            end_date=f"{end_year}1231",
        )
        if df is not None and not df.empty:
            df = self._filter_annual_reports(df)
            df = self._apply_mapping(df, "indicators")
        return df if df is not None else pd.DataFrame()

    def _fetch_market(self, ts_code: str) -> dict[str, Any]:
        """Fetch latest market data (daily_basic)"""
        df = self.api.daily_basic(ts_code=ts_code)
        if df is None or df.empty:
            return {}

        mapping = self.FIELD_MAPPINGS.get("market", {})
        row = df.iloc[0]

        result = {}
        for native, std in mapping.items():
            if native in df.columns:
                value = row.get(native)
                if value is not None and not pd.isna(value):
                    # Convert to scalar
                    if hasattr(value, 'item'):
                        value = value.item()
                    elif isinstance(value, pd.Series):
                        value = value.iloc[0] if not value.empty else None
                    if value is not None:
                        result[std] = float(value) if isinstance(value, (int, float)) else value

        # Fetch trading data (daily)
        try:
            df_daily = self.api.daily(ts_code=ts_code)
            if df_daily is not None and not df_daily.empty:
                trading_mapping = self.FIELD_MAPPINGS.get("daily", {})
                row_daily = df_daily.iloc[0]
                for native, std in trading_mapping.items():
                    if native in df_daily.columns:
                        value = row_daily.get(native)
                        if value is not None and not pd.isna(value):
                            if hasattr(value, 'item'):
                                value = value.item()
                            result[std] = float(value) if isinstance(value, (int, float)) else value
        except Exception:
            pass  # Trading data may not be available

        return result

    def _df_to_dict(
        self, df: pd.DataFrame, fields: set[str], date_col: str = "end_date"
    ) -> dict[str, dict[int, Any]]:
        """Convert DataFrame to {field: {year: value}}"""
        if df.empty:
            return {}

        result: dict[str, dict[int, Any]] = {f: {} for f in fields}

        for col in fields:
            if col not in df.columns:
                continue

            for _, row in df.iterrows():
                date_val = row.get(date_col)
                if date_val is None or (hasattr(date_val, '__float__') and pd.isna(date_val)):
                    continue

                year = pd.to_datetime(str(date_val)).year
                value = row.get(col)

                if value is not None and not (hasattr(value, '__float__') and pd.isna(value)):
                    # Convert to scalar
                    if isinstance(value, pd.Series):
                        value = value.iloc[0] if not value.empty else None
                    elif hasattr(value, 'item'):
                        value = value.item()
                    if value is not None:
                        result[col][year] = float(value) if isinstance(value, (int, float)) else value

        return result

    # ========================================================================
    # Public API (used by plugin hooks)
    # ========================================================================

    def fetch_financials(
        self,
        symbol: str,
        fields: set[str],
        end_year: int,
        years: int = 10,
    ) -> dict[str, dict[int, Any]] | None:
        """Fetch financial statement data

        Args:
            symbol: Stock code
            fields: IFRS standard field names
            end_year: End year
            years: Number of years

        Returns:
            {field: {year: value}} or None
        """
        # Filter out indicator and market fields
        fs_fields = fields - self._INDICATOR_FIELDS - self._MARKET_FIELDS
        if not fs_fields:
            return None

        ts_code = self._to_ts_code(symbol)
        start_year = end_year - years + 1

        results: dict[str, dict[int, Any]] = {f: {} for f in fs_fields}

        # Determine which statements to fetch
        balance_fields = fs_fields & self._BALANCE_FIELDS
        income_fields = fs_fields & self._INCOME_FIELDS
        cash_fields = fs_fields & self._CASH_FIELDS

        # Fetch and merge
        if balance_fields:
            df = self._fetch_balance_sheet(ts_code, start_year, end_year)
            results.update(self._df_to_dict(df, balance_fields))

        if income_fields:
            df = self._fetch_income_statement(ts_code, start_year, end_year)
            results.update(self._df_to_dict(df, income_fields))

        if cash_fields:
            df = self._fetch_cash_flow(ts_code, start_year, end_year)
            results.update(self._df_to_dict(df, cash_fields))

        return results if any(results.values()) else None

    def fetch_indicators(
        self,
        symbol: str,
        fields: set[str],
        end_year: int,
        years: int = 10,
    ) -> dict[str, dict[int, Any]] | None:
        """Fetch financial indicators

        Args:
            symbol: Stock code
            fields: IFRS indicator field names
            end_year: End year
            years: Number of years

        Returns:
            {field: {year: value}} or None
        """
        indicator_fields = fields & self._INDICATOR_FIELDS
        if not indicator_fields:
            return None

        ts_code = self._to_ts_code(symbol)
        start_year = end_year - years + 1

        df = self._fetch_indicators(ts_code, start_year, end_year)
        return self._df_to_dict(df, indicator_fields) if not df.empty else None

    def fetch_market(
        self,
        symbol: str,
        fields: set[str],
    ) -> dict[str, Any]:
        """Fetch market data

        Args:
            symbol: Stock code
            fields: Market/trading field names

        Returns:
            {field: value}
        """
        # 支持市场数据和交易数据字段
        supported = self._MARKET_FIELDS | self._TRADING_FIELDS
        requested_fields = fields & supported
        if not requested_fields:
            return {}

        ts_code = self._to_ts_code(symbol)
        result = self._fetch_market(ts_code)

        # Filter to requested fields
        return {k: v for k, v in result.items() if k in requested_fields}
