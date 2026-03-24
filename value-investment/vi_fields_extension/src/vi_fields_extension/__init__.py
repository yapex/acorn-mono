"""VI Fields Extension - Field Extension Registry

提供扩展字段的能力。

使用方式：

    from vi_fields_extension import register_fields

    register_fields(
        source="wind",
        fields={
            "sector": "所属行业",
            "dividend_yield": "股息率",
        }
    )

或者通过实现 FieldRegistrySpec 直接贡献字段：

    import pluggy

    vi_hookimpl = pluggy.HookimplMarker("value_investment")

    class MyFieldsPlugin:
        @vi_hookimpl
        def vi_fields(self):
            return {
                "source": "my_plugin",
                "fields": {...}
            }

内置字段定义在 standard_fields.py 中。
"""
from __future__ import annotations

from .standard_fields import (
    IFRS_FIELDS,
    CUSTOM_FIELDS,
    ALL_BUILTIN_FIELDS,
    FIELD_TO_SOURCE,
    FIELD_DEFINITIONS,
    StandardFields,
)

# Global registry for extension fields
_extension_fields: dict[str, dict[str, dict]] = {}


def register_fields(source: str, fields: dict[str, str]) -> None:
    """注册扩展字段

    Args:
        source: 插件/来源名称 (e.g. "wind", "bloomberg")
        fields: Dict of {field_name: description}

    Example:
        register_fields(
            source="wind",
            fields={
                "sector": "所属行业",
                "dividend_yield": "股息率",
            }
        )
    """
    global _extension_fields

    _extension_fields[source] = {
        name: {"description": desc}
        for name, desc in fields.items()
    }


def get_extension_fields() -> dict[str, dict[str, dict]]:
    """获取所有注册的扩展字段"""
    return _extension_fields.copy()


def clear() -> None:
    """清除所有注册的扩展字段（用于测试）"""
    global _extension_fields
    _extension_fields.clear()


# =============================================================================
# Pre-register built-in custom fields
# =============================================================================

_builtin_fields = {
    "close": "收盘价",
    "open": "开盘价",
    "high": "最高价",
    "low": "最低价",
    "volume": "成交量",
    "goodwill": "商誉",
    "intangible_assets": "无形资产",
    "long_term_investment": "长期股权投资",
    "construction_in_progress": "在建工程",
    "long_term_debt": "长期借款",
    "short_term_debt": "短期借款",
    "short_term_borrowings": "短期借款",
    "parent_net_profit": "归属母公司净利润",
    "bond_payable": "应付债券",
    "other_receivables": "其他应收款",
    "non_current_liabilities_due_1y": "一年内到期的非流动负债",
    "main_business_income": "主营业务收入",
    "interest_expense": "利息支出",
    "interest_income": "利息收入",
    "non_operating_income": "营业外收入",
    "investment_income": "投资收益",
    "fair_value_change": "公允价值变动损益",
    "cash_ratio": "现金比率",
    "ocf_to_debt": "OCF/带息债务",
    "interest_bearing_debt": "带息债务",
    "ebitda": "EBITDA",
    "currentdebt_to_debt": "流动负债/总负债",
    "revenue_yoy": "营业收入同比增长率",
    "net_profit_yoy": "净利润同比增长率",
    "roic": "投入资本回报率",
    "operating_profit_margin": "营业利润率",
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
    "circ_market_cap": "流通市值",
    "circ_shares": "流通股本",
}

_extension_fields["builtin"] = {
    name: {"description": desc}
    for name, desc in _builtin_fields.items()
}

# Export plugin
from .plugin import plugin
