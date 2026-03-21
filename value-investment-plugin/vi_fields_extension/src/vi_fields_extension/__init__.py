"""VI Fields Extension - Field Extension Registry

Simple way to register custom fields:

    from vi_fields_extension import register_fields

    register_fields(
        source="my_plugin",
        fields={
            "sector": "所属行业",
            "dividend_yield": "股息率",
        }
    )

Pre-registered fields from Tushare data provider.
"""
from __future__ import annotations

# Global registry
_custom_fields: dict[str, set] = {}
_descriptions: dict[str, dict[str, str]] = {}


def register_fields(source: str, fields: dict[str, str]) -> None:
    """Register custom fields

    Args:
        source: Plugin/来源名称 (e.g. "tushare", "my_plugin")
        fields: Dict of {field_name: description}

    Example:
        register_fields(
            source="tushare",
            fields={
                "sector": "所属行业",
                "dividend_yield": "股息率",
            }
        )
    """
    global _custom_fields, _descriptions

    field_names = set(fields.keys())
    _custom_fields[source] = field_names
    _descriptions[source] = fields


def get_fields() -> dict[str, set]:
    """Get all registered fields by source"""
    return _custom_fields.copy()


def get_descriptions() -> dict[str, dict[str, str]]:
    """Get all field descriptions"""
    return _descriptions.copy()


def clear() -> None:
    """Clear all registered fields (for testing)"""
    global _custom_fields, _descriptions
    _custom_fields.clear()
    _descriptions.clear()


# =============================================================================
# Pre-registered fields from Tushare data provider
# =============================================================================

_TUSHARE_FIELDS = {
    # Trading Data
    "close": "收盘价",
    # Balance Sheet
    "goodwill": "商誉",
    "intangible_assets": "无形资产",
    "long_term_investment": "长期股权投资",
    "construction_in_progress": "在建工程",
    "long_term_debt": "长期借款",
    "short_term_debt": "短期借款",
    "short_term_borrowings": "短期借款",
    "parent_net_profit": "归属母公司净利润",
    "net_debt": "净债务",
    "ebit": "息税前利润",
    "free_cash_flow_to_firm": "企业自由现金流",
    "free_cash_flow_to_equity": "股权自由现金流",
    "ocf_to_short_debt": "OCF/短期债务",
    "debt_to_equity": "产权比率",
    "long_term_debt_ratio": "长期债务占比",
    "current_assets_ratio": "流动资产占比",
    "selling_expense_ratio": "销售费用率",
    "admin_expense_ratio": "管理费用率",
    "finance_expense_ratio": "财务费用率",
    "total_assets_yoy": "总资产同比增长率",
    "equity_yoy": "净资产同比增长率",
    "operating_cash_flow_yoy": "经营活动现金流同比增长率",
    "cash_ratio": "现金比率",
    "ocf_to_debt": "OCF/带息债务",
    "interest_bearing_debt": "带息债务",
    "ebitda": "EBITDA",
    "currentdebt_to_debt": "流动负债/总负债",
    "revenue_yoy": "营业收入同比增长率",
    "net_profit_yoy": "净利润同比增长率",
    "interest_expense": "利息支出",
    "interest_income": "利息收入",
    "non_current_liabilities_due_1y": "一年内到期的非流动负债",
    "bond_payable": "应付债券",
    "other_receivables": "其他应收款",
    "non_operating_income": "营业外收入",
    "investment_income": "投资收益",
    "fair_value_change": "公允价值变动损益",
    "main_business_income": "主营业务收入",
}

# Pre-register Tushare fields
register_fields(source="tushare", fields=_TUSHARE_FIELDS)
