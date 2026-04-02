"""HK Provider Implementation

从 AKShare API 获取港股市场数据。

继承 BaseDataProvider，自动获得：
- 字段映射（_apply_mapping）
- 数据去重（默认按日期）
- 模板方法（fetch_financials, fetch_indicators, fetch_market）
"""
from __future__ import annotations

import warnings

import akshare as ak
import pandas as pd

from vi_core import BaseDataProvider
from vi_core.base_provider import get_ttl_until_june_next_year
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
            "股东应占溢利": StandardFields.net_profit,  # 归母净利润直接映射为 net_profit
            # EPS
            # EPS
            "每股基本盈利": StandardFields.basic_eps,
            # 费用
            "营业成本": StandardFields.operating_cost,
            "销售成本": StandardFields.operating_cost,
            "行政开支": StandardFields.administrative_expenses,
            "销售及分销费用": StandardFields.selling_distribution_expenses,
            "融资成本": StandardFields.finance_cost,
            "税项": StandardFields.income_tax,
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
            # 每股数据 - 从利润表获取更准确的历史数据
            # "基本每股收益(元)": StandardFields.basic_eps,  # 移除，使用利润表中的每股基本盈利
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
        # 港股历史财务指标 (来自 stock_financial_hk_analysis_indicator_em)
        "hk_indicators": {
            "BASIC_EPS": StandardFields.basic_eps,
            "DILUTED_EPS": StandardFields.diluted_eps,
            "BPS": StandardFields.book_value_per_share,
            "OPERATE_INCOME": StandardFields.total_revenue,
            "GROSS_PROFIT": StandardFields.gross_profit,
            "HOLDER_PROFIT": StandardFields.parent_net_profit,
            "ROE_AVG": StandardFields.roe,
            "ROE_YEARLY": StandardFields.roe,
            "ROA": StandardFields.roa,
            "GROSS_PROFIT_RATIO": StandardFields.gross_margin,
            "NET_PROFIT_RATIO": StandardFields.net_profit_margin,
            "DEBT_ASSET_RATIO": StandardFields.debt_ratio,
            "CURRENT_RATIO": StandardFields.current_ratio,
            "CURRENTDEBT_DEBT": StandardFields.currentdebt_to_debt,
            "ROIC_YEARLY": StandardFields.roic,
        },
        "market": {
            # 市值
            "总市值(港元)": StandardFields.market_cap,
            "港股市值(港元)": StandardFields.market_cap,
            # 估值
            "市盈率": StandardFields.pe_ratio,
            "市净率": StandardFields.pb_ratio,
            # 股价 (从日线数据获取)
            "close": StandardFields.close,
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

    def _get_financial_ttl(self, end_year: int) -> int:
        """港股财务数据缓存到次年6月底
        
        港股年报一般在6月底前发布。
        """
        return get_ttl_until_june_next_year(end_year)

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
            result = result.merge(df, on=StandardFields.fiscal_year, how="outer", suffixes=("", "_dup"))
            dup_cols = [c for c in result.columns if c.endswith("_dup")]
            result = result.drop(columns=dup_cols)

        # 港股部分公司（如腾讯、阿里）利润表中没有「营业成本」或「销售成本」，
        # 但有「营业额」和「毛利」，此时 operating_cost = 营业额 - 毛利
        if "营业成本" not in result.columns and "销售成本" not in result.columns:
            if "营业额" in result.columns and "毛利" in result.columns:
                result = result.copy()
                result["营业成本"] = result["营业额"] - result["毛利"]

        return result

    def _apply_mapping(self, df: pd.DataFrame) -> pd.DataFrame:
        """应用字段映射"""
        if df is None or df.empty:
            return df

        # 调用父类方法进行标准映射
        df = super()._apply_mapping(df)

        return df

    def _fetch_indicators_impl(
        self,
        symbol: str,
        start_year: int,
        end_year: int,
    ) -> pd.DataFrame | None:
        """获取财务指标数据（使用历史数据接口）"""
        try:
            # 使用返回历史数据的接口
            df = ak.stock_financial_hk_analysis_indicator_em(symbol=symbol)
            if df is None or df.empty:
                return None

            df = df.copy()

            # 从 REPORT_DATE 提取年份
            df[StandardFields.fiscal_year] = pd.to_datetime(df["REPORT_DATE"]).dt.year

            # 按年份过滤
            df = df[(df[StandardFields.fiscal_year] >= start_year) & (df[StandardFields.fiscal_year] <= end_year)]

            # 按年份排序（降序）
            df = df.sort_values(StandardFields.fiscal_year, ascending=False)

            # 删除不需要的列
            cols_to_drop = ["SECUCODE", "SECURITY_CODE", "SECURITY_NAME_ABBR", "ORG_CODE",
                           "REPORT_DATE", "DATE_TYPE_CODE", "START_DATE", "FISCAL_YEAR",
                           "CURRENCY", "IS_CNY_CODE"]
            df = df.drop(columns=[c for c in cols_to_drop if c in df.columns])

            return df
        except Exception:
            return None

    def _fetch_market_impl(
        self,
        symbol: str,
        end_year: int | None = None,
        years: int = 10,
    ) -> pd.DataFrame | None:
        """获取市场数据
        
        从日线数据获取年末收盘价。
        如果指定了年份范围，返回每年最后一个交易日的收盘价。
        如果未指定年份，返回每年最后一个交易日的收盘价（最多10年）。
        """
        try:
            # 获取历史日线数据
            df = ak.stock_hk_daily(symbol=symbol, adjust="qfq")
            if df is None or df.empty:
                return None

            # 确认列名
            date_col = "date" if "date" in df.columns else "日期"
            close_col = "close" if "close" in df.columns else "收盘"

            if date_col not in df.columns or close_col not in df.columns:
                return None

            # 转换日期列
            df[date_col] = pd.to_datetime(df[date_col])
            df = df.sort_values(date_col)

            # 提取年份
            df["_year"] = df[date_col].dt.year

            # 确定年份范围
            available_years = sorted(df["_year"].unique(), reverse=True)

            # 计算起始年份
            start_year = (end_year - years + 1) if end_year else None

            if start_year and end_year:
                target_years = [y for y in available_years if start_year <= y <= end_year]
            elif end_year:
                target_years = [y for y in available_years if y <= end_year]
            else:
                # 默认取最近years年
                target_years = available_years[:years]

            # 取每年最后一个交易日的收盘价
            result_rows = []
            for year in target_years:
                year_data = df[df["_year"] == year]
                if not year_data.empty:
                    last_day = year_data.iloc[-1]
                    result_rows.append({
                        StandardFields.fiscal_year: year,
                        StandardFields.close: last_day[close_col],
                    })

            if not result_rows:
                return None

            return pd.DataFrame(result_rows)
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
            df[StandardFields.fiscal_year] = pd.to_datetime(df["REPORT_DATE"]).dt.year

        try:
            wide_df = df.pivot_table(
                index=StandardFields.fiscal_year,
                columns=item_col,
                values="AMOUNT",
                aggfunc="first",
            )
            result = wide_df.reset_index()
            # 移除不需要的元数据列
            cols_to_drop = [c for c in result.columns if c in ["STD_ITEM_NAME", "ITEM_NAME", "AMOUNT", "SECUCODE", "SECURITY_CODE", "SECURITY_NAME_ABBR", "ORG_CODE", "DATE_TYPE_CODE", "FISCAL_YEAR", "START_DATE", "STD_REPORT_DATE"]]
            if cols_to_drop:
                result = result.drop(columns=cols_to_drop)
            return result
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
