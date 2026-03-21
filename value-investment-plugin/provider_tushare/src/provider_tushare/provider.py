"""Tushare Provider Implementation

从 Tushare API 获取 A 股市场数据。
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


class TushareProvider:
    """Tushare data provider for A 股 market"""

    # 所有支持的字段
    SUPPORTED_FIELDS: set[str] = {
        # --- 资产负债表 ---
        "total_assets",
        "total_liabilities",
        "total_equity",
        "current_assets",
        "current_liabilities",
        "cash_and_equivalents",
        "inventory",
        "accounts_receivable",
        "accounts_payable",
        "fixed_assets",
        "prepayment",
        "contract_assets",
        "contract_liab",
        "total_shares",
        "goodwill",
        "intangible_assets",
        "long_term_investment",
        "construction_in_progress",
        "short_term_borrowings",
        "long_term_debt",
        "non_current_liabilities_due_1y",
        "bond_payable",
        "other_receivables",
        # --- 利润表 ---
        "total_revenue",
        "main_business_income",
        "net_profit",
        "operating_profit",
        "operating_cost",
        "parent_net_profit",
        "interest_expense",
        "interest_income",
        "non_operating_income",
        "investment_income",
        "fair_value_change",
        # --- 现金流量表 ---
        "operating_cash_flow",
        "investing_cash_flow",
        "financing_cash_flow",
        "capital_expenditure",
        # --- 财务指标 ---
        "roe",
        "roa",
        "gross_margin",
        "net_profit_margin",
        "current_ratio",
        "quick_ratio",
        "debt_ratio",
        "asset_turnover",
        "receivable_turnover",
        "roic",
        "basic_eps",
        "diluted_eps",
        "book_value_per_share",
        "cash_ratio",
        "ocf_to_debt",
        "interest_bearing_debt",
        "ebitda",
        "currentdebt_to_debt",
        "operating_profit_margin",
        "revenue_yoy",
        "net_profit_yoy",
        # --- 计算字段 ---
        "net_debt",
        "ebit",
        "free_cash_flow_to_firm",
        "free_cash_flow_to_equity",
        "ocf_to_short_debt",
        "debt_to_equity",
        "long_term_debt_ratio",
        "current_assets_ratio",
        "selling_expense_ratio",
        "admin_expense_ratio",
        "finance_expense_ratio",
        "total_assets_yoy",
        "equity_yoy",
        "operating_cash_flow_yoy",
        # --- 市场数据 ---
        "market_cap",
        "circ_market_cap",
        "circ_shares",
        "pe_ratio",
        "pb_ratio",
    }

    # 字段映射
    FIELD_MAPPINGS: dict[str, dict[str, str]] = {
        "balance_sheet": {
            "total_assets": "total_assets",
            "total_liab": "total_liabilities",
            "total_hldr_eqy_exc_min_int": "total_equity",
            "total_cur_liab": "current_liabilities",
            "money_cap": "cash_and_equivalents",
            "inventories": "inventory",
            "accounts_receiv": "accounts_receivable",
            "fix_assets": "fixed_assets",
            "total_cur_assets": "current_assets",
            "accounts_pay": "accounts_payable",
            "prepayment": "prepayment",
            "contract_assets": "contract_assets",
            "contract_liab": "contract_liab",
            "adv_receipts": "adv_receipts",
            "total_share": "total_shares",
            "goodwill": "goodwill",
            "intan_assets": "intangible_assets",
            "lt_eqt_invest": "long_term_investment",
            "cip": "construction_in_progress",
            "st_borr": "short_term_borrowings",
            "lt_borr": "long_term_debt",
            "non_cur_liab_due_1y": "non_current_liabilities_due_1y",
            "bond_payable": "bond_payable",
            "oth_receiv": "other_receivables",
        },
        "income_statement": {
            "total_revenue": "total_revenue",
            "revenue": "main_business_income",
            "n_income": "net_profit",
            "operate_profit": "operating_profit",
            "oper_cost": "operating_cost",
            "n_income_attr_p": "parent_net_profit",
            "int_exp": "interest_expense",
            "int_income": "interest_income",
            "non_oper_income": "non_operating_income",
            "invest_income": "investment_income",
            "fv_value_chg_gain": "fair_value_change",
        },
        "cash_flow": {
            "n_cashflow_act": "operating_cash_flow",
            "n_cashflow_inv_act": "investing_cash_flow",
            "n_cash_flows_fnc_act": "financing_cash_flow",
            "c_pay_acq_const_fiolta": "capital_expenditure",
        },
        "indicators": {
            "roe": "roe",
            "roa": "roa",
            "grossprofit_margin": "gross_margin",
            "netprofit_margin": "net_profit_margin",
            "current_ratio": "current_ratio",
            "quick_ratio": "quick_ratio",
            "debt_to_assets": "debt_ratio",
            "assets_turn": "asset_turnover",
            "ar_turn": "receivable_turnover",
            "roic": "roic",
            "eps": "basic_eps",
            "dt_eps": "diluted_eps",
            "bps": "book_value_per_share",
            "cash_ratio": "cash_ratio",
            "ocf_to_debt": "ocf_to_debt",
            "interestdebt": "interest_bearing_debt",
            "ebitda": "ebitda",
            "currentdebt_to_debt": "currentdebt_to_debt",
            "op_of_gr": "operating_profit_margin",
            "tr_yoy": "revenue_yoy",
            "netprofit_yoy": "net_profit_yoy",
            "netdebt": "net_debt",
            "ebit": "ebit",
            "fcff": "free_cash_flow_to_firm",
            "fcfe": "free_cash_flow_to_equity",
            "ocf_to_shortdebt": "ocf_to_short_debt",
            "debt_to_eqt": "debt_to_equity",
            "longdeb_to_debt": "long_term_debt_ratio",
            "ca_to_assets": "current_assets_ratio",
            "saleexp_to_gr": "selling_expense_ratio",
            "adminexp_of_gr": "admin_expense_ratio",
            "finaexp_of_gr": "finance_expense_ratio",
            "assets_yoy": "total_assets_yoy",
            "eqt_yoy": "equity_yoy",
            "ocf_yoy": "operating_cash_flow_yoy",
        },
        "market": {
            "total_mv": "market_cap",
            "circ_mv": "circ_market_cap",
            "float_share": "circ_shares",
            "pe_ttm": "pe_ratio",
            "pb": "pb_ratio",
            "total_share": "total_shares",
        },
    }

    # 财务指标字段集合
    _INDICATOR_FIELDS: set[str] = {
        "roe", "roa", "gross_margin", "net_profit_margin",
        "current_ratio", "quick_ratio", "debt_ratio", "asset_turnover",
        "receivable_turnover", "roic", "basic_eps", "diluted_eps",
        "book_value_per_share", "cash_ratio", "ocf_to_debt",
        "interest_bearing_debt", "ebitda", "currentdebt_to_debt",
        "operating_profit_margin", "revenue_yoy", "net_profit_yoy",
        "net_debt", "ebit", "free_cash_flow_to_firm", "free_cash_flow_to_equity",
        "ocf_to_short_debt", "debt_to_equity", "long_term_debt_ratio",
        "current_assets_ratio", "selling_expense_ratio", "admin_expense_ratio",
        "finance_expense_ratio", "total_assets_yoy", "equity_yoy", "operating_cash_flow_yoy",
    }

    # 市场数据字段
    _MARKET_FIELDS: set[str] = {
        "market_cap", "circ_market_cap", "circ_shares", "pe_ratio", "pb_ratio", "total_shares",
    }

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
        """Fetch latest market data"""
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
        balance_fields = fs_fields & {
            "total_assets", "total_liabilities", "total_equity",
            "current_assets", "current_liabilities", "cash_and_equivalents",
            "inventory", "accounts_receivable", "accounts_payable", "fixed_assets",
            "prepayment", "contract_assets", "contract_liab", "total_shares",
            "goodwill", "intangible_assets", "long_term_investment",
            "construction_in_progress", "short_term_borrowings", "long_term_debt",
            "non_current_liabilities_due_1y", "bond_payable", "other_receivables",
        }

        income_fields = fs_fields & {
            "total_revenue", "main_business_income", "net_profit", "operating_profit",
            "operating_cost", "parent_net_profit", "interest_expense", "interest_income",
            "non_operating_income", "investment_income", "fair_value_change",
        }

        cash_fields = fs_fields & {
            "operating_cash_flow", "investing_cash_flow", "financing_cash_flow",
            "capital_expenditure",
        }

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
            fields: Market field names

        Returns:
            {field: value}
        """
        market_fields = fields & self._MARKET_FIELDS
        if not market_fields:
            return {}

        ts_code = self._to_ts_code(symbol)
        result = self._fetch_market(ts_code)

        # Filter to requested fields
        return {k: v for k, v in result.items() if k in market_fields}
