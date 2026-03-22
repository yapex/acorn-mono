"""Standard Fields Definitions

系统标准字段的单一真相来源。

使用方式：
    from vi_fields_extension import StandardFields

    # Provider 映射
    FIELD_MAPPINGS = {
        "balance_sheet": {
            "total_assets": StandardFields.total_assets,
        }
    }

字段来源分类：
- ifrs: IFRS (International Financial Reporting Standards) 国际财务报告准则
- custom: 系统内置的扩展字段
"""
from __future__ import annotations


# =============================================================================
# 单一数据源：所有字段定义（名称、描述、分类、来源）
# =============================================================================

FIELD_DEFINITIONS: dict[str, dict] = {
    # =====================================================================
    # IFRS 标准字段
    # =====================================================================

    # Balance Sheet
    "total_assets": {"description": "资产总计", "category": "balance_sheet", "source": "ifrs"},
    "total_liabilities": {"description": "负债合计", "category": "balance_sheet", "source": "ifrs"},
    "total_equity": {"description": "所有者权益合计", "category": "balance_sheet", "source": "ifrs"},
    "current_assets": {"description": "流动资产", "category": "balance_sheet", "source": "ifrs"},
    "current_liabilities": {"description": "流动负债", "category": "balance_sheet", "source": "ifrs"},
    "cash_and_equivalents": {"description": "货币资金", "category": "balance_sheet", "source": "ifrs"},
    "inventory": {"description": "存货", "category": "balance_sheet", "source": "ifrs"},
    "accounts_receivable": {"description": "应收账款", "category": "balance_sheet", "source": "ifrs"},
    "accounts_payable": {"description": "应付账款", "category": "balance_sheet", "source": "ifrs"},
    "fixed_assets": {"description": "固定资产", "category": "balance_sheet", "source": "ifrs"},
    "prepayment": {"description": "预付款项", "category": "balance_sheet", "source": "ifrs"},
    "adv_receipts": {"description": "预收款项", "category": "balance_sheet", "source": "ifrs"},
    "contract_assets": {"description": "合同资产", "category": "balance_sheet", "source": "ifrs"},
    "contract_liab": {"description": "合同负债", "category": "balance_sheet", "source": "ifrs"},

    # Income Statement
    "total_revenue": {"description": "营业总收入", "category": "income_statement", "source": "ifrs"},
    "net_profit": {"description": "净利润", "category": "income_statement", "source": "ifrs"},
    "operating_profit": {"description": "营业利润", "category": "income_statement", "source": "ifrs"},
    "operating_cost": {"description": "营业成本", "category": "income_statement", "source": "ifrs"},

    # Cash Flow
    "operating_cash_flow": {"description": "经营活动现金流量净额", "category": "cash_flow", "source": "ifrs"},
    "investing_cash_flow": {"description": "投资活动现金流量净额", "category": "cash_flow", "source": "ifrs"},
    "financing_cash_flow": {"description": "筹资活动现金流量净额", "category": "cash_flow", "source": "ifrs"},
    "capital_expenditure": {"description": "资本支出", "category": "cash_flow", "source": "ifrs"},

    # Key Ratios
    "roe": {"description": "净资产收益率 (ROE)", "category": "ratio", "source": "ifrs"},
    "roa": {"description": "资产收益率 (ROA)", "category": "ratio", "source": "ifrs"},
    "gross_margin": {"description": "毛利率", "category": "ratio", "source": "ifrs"},
    "net_profit_margin": {"description": "净利率", "category": "ratio", "source": "ifrs"},
    "current_ratio": {"description": "流动比率", "category": "ratio", "source": "ifrs"},
    "quick_ratio": {"description": "速动比率", "category": "ratio", "source": "ifrs"},
    "debt_ratio": {"description": "资产负债率", "category": "ratio", "source": "ifrs"},
    "asset_turnover": {"description": "资产周转率", "category": "ratio", "source": "ifrs"},
    "receivable_turnover": {"description": "应收账款周转率", "category": "ratio", "source": "ifrs"},

    # Market Data
    "market_cap": {"description": "总市值", "category": "market", "source": "ifrs"},
    "total_shares": {"description": "总股本", "category": "market", "source": "ifrs"},
    "pe_ratio": {"description": "市盈率 (P/E)", "category": "market", "source": "ifrs"},
    "pb_ratio": {"description": "市净率 (P/B)", "category": "market", "source": "ifrs"},
    "basic_eps": {"description": "基本每股收益", "category": "market", "source": "ifrs"},
    "diluted_eps": {"description": "稀释每股收益", "category": "market", "source": "ifrs"},
    "book_value_per_share": {"description": "每股净资产", "category": "market", "source": "ifrs"},

    # =====================================================================
    # Custom 扩展字段
    # =====================================================================

    # Trading Data
    "close": {"description": "收盘价", "category": "trading", "source": "custom"},
    "open": {"description": "开盘价", "category": "trading", "source": "custom"},
    "high": {"description": "最高价", "category": "trading", "source": "custom"},
    "low": {"description": "最低价", "category": "trading", "source": "custom"},
    "volume": {"description": "成交量", "category": "trading", "source": "custom"},

    # Balance Sheet (extended)
    "goodwill": {"description": "商誉", "category": "balance_sheet", "source": "custom"},
    "intangible_assets": {"description": "无形资产", "category": "balance_sheet", "source": "custom"},
    "long_term_investment": {"description": "长期股权投资", "category": "balance_sheet", "source": "custom"},
    "construction_in_progress": {"description": "在建工程", "category": "balance_sheet", "source": "custom"},
    "long_term_debt": {"description": "长期借款", "category": "balance_sheet", "source": "custom"},
    "short_term_debt": {"description": "短期借款", "category": "balance_sheet", "source": "custom"},
    "short_term_borrowings": {"description": "短期借款", "category": "balance_sheet", "source": "custom"},
    "parent_net_profit": {"description": "归属母公司净利润", "category": "income_statement", "source": "custom"},
    "bond_payable": {"description": "应付债券", "category": "balance_sheet", "source": "custom"},
    "other_receivables": {"description": "其他应收款", "category": "balance_sheet", "source": "custom"},
    "non_current_liabilities_due_1y": {"description": "一年内到期的非流动负债", "category": "balance_sheet", "source": "custom"},

    # Income Statement (extended)
    "main_business_income": {"description": "主营业务收入", "category": "income_statement", "source": "custom"},
    "interest_expense": {"description": "利息支出", "category": "income_statement", "source": "custom"},
    "interest_income": {"description": "利息收入", "category": "income_statement", "source": "custom"},
    "non_operating_income": {"description": "营业外收入", "category": "income_statement", "source": "custom"},
    "investment_income": {"description": "投资收益", "category": "income_statement", "source": "custom"},
    "fair_value_change": {"description": "公允价值变动损益", "category": "income_statement", "source": "custom"},

    # Financial Ratios (extended)
    "cash_ratio": {"description": "现金比率", "category": "ratio", "source": "custom"},
    "ocf_to_debt": {"description": "OCF/带息债务", "category": "ratio", "source": "custom"},
    "interest_bearing_debt": {"description": "带息债务", "category": "ratio", "source": "custom"},
    "ebitda": {"description": "EBITDA", "category": "ratio", "source": "custom"},
    "currentdebt_to_debt": {"description": "流动负债/总负债", "category": "ratio", "source": "custom"},
    "revenue_yoy": {"description": "营业收入同比增长率", "category": "ratio", "source": "custom"},
    "net_profit_yoy": {"description": "净利润同比增长率", "category": "ratio", "source": "custom"},
    "roic": {"description": "投入资本回报率", "category": "ratio", "source": "custom"},
    "operating_profit_margin": {"description": "营业利润率", "category": "ratio", "source": "custom"},

    # Calculated Fields
    "net_debt": {"description": "净债务", "category": "calculated", "source": "custom"},
    "ebit": {"description": "息税前利润", "category": "calculated", "source": "custom"},
    "free_cash_flow_to_firm": {"description": "企业自由现金流", "category": "calculated", "source": "custom"},
    "free_cash_flow_to_equity": {"description": "股权自由现金流", "category": "calculated", "source": "custom"},
    "ocf_to_short_debt": {"description": "OCF/短期债务", "category": "calculated", "source": "custom"},
    "debt_to_equity": {"description": "产权比率", "category": "calculated", "source": "custom"},
    "long_term_debt_ratio": {"description": "长期债务占比", "category": "calculated", "source": "custom"},
    "current_assets_ratio": {"description": "流动资产占比", "category": "calculated", "source": "custom"},
    "selling_expense_ratio": {"description": "销售费用率", "category": "calculated", "source": "custom"},
    "admin_expense_ratio": {"description": "管理费用率", "category": "calculated", "source": "custom"},
    "finance_expense_ratio": {"description": "财务费用率", "category": "calculated", "source": "custom"},
    "total_assets_yoy": {"description": "总资产同比增长率", "category": "ratio", "source": "custom"},
    "equity_yoy": {"description": "净资产同比增长率", "category": "ratio", "source": "custom"},
    "operating_cash_flow_yoy": {"description": "经营活动现金流同比增长率", "category": "ratio", "source": "custom"},

    # Market Data (extended)
    "circ_market_cap": {"description": "流通市值", "category": "market", "source": "custom"},
    "circ_shares": {"description": "流通股本", "category": "market", "source": "custom"},

    # =====================================================================
    # HK Market 特有字段
    # =====================================================================

    # HK 特有市场数据
    "hk_market_cap": {"description": "港股市值(港元)", "category": "market", "source": "hk"},
    "hk_dividend_per_share": {"description": "每股股息TTM(港元)", "category": "market", "source": "hk"},
    "hk_dividend_yield_ttm": {"description": "股息率TTM(%)", "category": "market", "source": "hk"},
    "hk_dividend_payout_ratio": {"description": "派息比率(%)", "category": "market", "source": "hk"},
    "hk_total_revenue_growth_qoq": {"description": "营业总收入滚动环比增长(%)", "category": "ratio", "source": "hk"},
    "hk_net_profit_growth_qoq": {"description": "净利润滚动环比增长(%)", "category": "ratio", "source": "hk"},

    # HK Balance Sheet 特有字段
    "shareholders_equity": {"description": "股东权益", "category": "balance_sheet", "source": "hk"},
    "share_capital": {"description": "股本", "category": "balance_sheet", "source": "hk"},
    "share_premium": {"description": "股本溢价", "category": "balance_sheet", "source": "hk"},
    "retained_earnings": {"description": "保留溢利(累计亏损)", "category": "balance_sheet", "source": "hk"},
    "investment_in_associates": {"description": "联营公司权益", "category": "balance_sheet", "source": "hk"},
    "investment_in_joint_ventures": {"description": "合营公司权益", "category": "balance_sheet", "source": "hk"},
    "non_current_assets": {"description": "非流动资产", "category": "balance_sheet", "source": "hk"},
    "non_current_liabilities": {"description": "非流动负债", "category": "balance_sheet", "source": "hk"},
    "short_term_debt": {"description": "短期贷款", "category": "balance_sheet", "source": "hk"},
    "long_term_debt": {"description": "长期贷款", "category": "balance_sheet", "source": "hk"},

    # HK Income Statement 特有字段
    "gross_profit": {"description": "毛利", "category": "income_statement", "source": "hk"},
    "profit_before_tax": {"description": "除税前溢利", "category": "income_statement", "source": "hk"},
    "profit_after_tax": {"description": "除税后溢利", "category": "income_statement", "source": "hk"},
    "administrative_expenses": {"description": "行政开支", "category": "income_statement", "source": "hk"},
    "selling_distribution_expenses": {"description": "销售及分销费用", "category": "income_statement", "source": "hk"},
    "finance_cost": {"description": "融资成本", "category": "income_statement", "source": "hk"},
    "depreciation_amortization": {"description": "折旧及摊销", "category": "income_statement", "source": "hk"},
    "operating_cash_flow_per_share": {"description": "每股经营现金流", "category": "market", "source": "hk"},

    # HK Cash Flow 特有字段
    "capital_expenditure_intangible": {"description": "购建无形资产及其他资产", "category": "cash_flow", "source": "hk"},
    "interest_paid_operating": {"description": "已付利息(经营)", "category": "cash_flow", "source": "hk"},
    "interest_paid_financing": {"description": "已付利息(融资)", "category": "cash_flow", "source": "hk"},
    "taxes_paid": {"description": "已付税项", "category": "cash_flow", "source": "hk"},
    "interest_received": {"description": "已收利息(投资)", "category": "cash_flow", "source": "hk"},
    "dividend_received": {"description": "已收股息(投资)", "category": "cash_flow", "source": "hk"},
    "cash_begin": {"description": "期初现金", "category": "cash_flow", "source": "hk"},
    "cash_end": {"description": "期末现金", "category": "cash_flow", "source": "hk"},
    "net_cash_change": {"description": "现金净额", "category": "cash_flow", "source": "hk"},
}


# =============================================================================
# 自动派生：来源分类（从 FIELD_DEFINITIONS 自动生成）
# =============================================================================

IFRS_FIELDS: set[str] = {
    name for name, info in FIELD_DEFINITIONS.items() if info.get("source") == "ifrs"
}

CUSTOM_FIELDS: set[str] = {
    name for name, info in FIELD_DEFINITIONS.items() if info.get("source") == "custom"
}


# =============================================================================
# 自动派生：字段常量类（从 FIELD_DEFINITIONS 自动生成）
# =============================================================================

class _StandardField(str):
    """字段常量类，实例即字符串值"""

    def __new__(cls, value: str):
        return super().__new__(cls, value)


class _StandardFieldsMeta(type):
    """元类：支持属性访问和 IDE 自动补全"""

    def __getattr__(cls, name: str) -> str:
        if name in FIELD_DEFINITIONS:
            return name
        raise AttributeError(f"'{cls.__name__}' has no field '{name}'")

    def __iter__(cls):
        """支持 for field in StandardFields 遍历所有字段名"""
        return iter(FIELD_DEFINITIONS.keys())

    def __len__(cls):
        return len(FIELD_DEFINITIONS)


class StandardFields(metaclass=_StandardFieldsMeta):
    """系统标准字段常量集合

    Provider 使用这些常量引用字段，避免硬编码：
        FIELD_MAPPINGS = {
            "balance_sheet": {
                "total_assets": StandardFields.total_assets,
            }
        }

    所有属性都是字符串值，如 StandardFields.total_assets == "total_assets"
    """

    pass  # 所有属性通过元类动态提供


# =============================================================================
# 便捷访问（从 FIELD_DEFINITIONS 自动生成）
# =============================================================================

# 所有内置字段
ALL_BUILTIN_FIELDS = set(FIELD_DEFINITIONS.keys())

# 字段到来源的映射
FIELD_TO_SOURCE: dict[str, str] = {
    name: info.get("source", "unknown") for name, info in FIELD_DEFINITIONS.items()
}
