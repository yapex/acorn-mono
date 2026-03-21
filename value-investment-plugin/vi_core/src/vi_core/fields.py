"""Field definitions for Value Investment

Three layers:
1. IFRSFields - International standard fields (frozen, immutable)
2. SourceFields - Data source fields (from Provider)
3. IndicatorFields - Derived indicators (from Calculator)
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class FieldType(Enum):
    """Field value types"""
    CURRENCY = "currency"       # 元 (RMB)
    RATIO = "ratio"            # 比率 (e.g. 1.5)
    PERCENTAGE = "percentage"  # 百分比 (e.g. 0.3 = 30%)
    NUMBER = "number"          # 数量
    MULTIPLE = "multiple"      # 倍数 (e.g. PE)


@dataclass(frozen=True)
class FieldSpec:
    """Field specification"""
    name: str           # Field name, e.g. "total_revenue"
    type: FieldType     # Value type
    unit: str           # Unit display, e.g. "元", "%"
    description: str    # Chinese description
    source: str         # "ifrs" | "provider" | "calculator"
    provider: str | None = None  # Which provider provides this field


# =============================================================================
# IFRS Fields - International Standard (frozen)
# =============================================================================

class IFRSFieldsMeta(type):
    """Metaclass to freeze IFRSFields"""

    def __setattr__(cls, name: str, value: Any) -> None:
        if name.isupper() and getattr(cls, "_frozen", False):
            raise AttributeError(
                f"IFRSFields is frozen. Cannot add '{name}'. "
                f"Add new fields to SourceFields."
            )
        super().__setattr__(name, value)


class IFRSFields(metaclass=IFRSFieldsMeta):
    """International Financial Reporting Standards fields
    
    These are standard fields provided directly by data sources.
    """
    _frozen: bool = False

    # Balance Sheet
    TOTAL_ASSETS = "total_assets"
    TOTAL_LIABILITIES = "total_liabilities"
    TOTAL_EQUITY = "total_equity"
    CURRENT_ASSETS = "current_assets"
    CURRENT_LIABILITIES = "current_liabilities"
    CASH_AND_EQUIVALENTS = "cash_and_equivalents"
    INVENTORY = "inventory"
    ACCOUNTS_RECEIVABLE = "accounts_receivable"
    ACCOUNTS_PAYABLE = "accounts_payable"
    FIXED_ASSETS = "fixed_assets"
    PREPAYMENT = "prepayment"
    ADV_RECEIPTS = "adv_receipts"
    CONTRACT_ASSETS = "contract_assets"
    CONTRACT_LIAB = "contract_liab"

    # Income Statement
    TOTAL_REVENUE = "total_revenue"
    NET_PROFIT = "net_profit"
    OPERATING_PROFIT = "operating_profit"
    OPERATING_COST = "operating_cost"

    # Cash Flow
    OPERATING_CASH_FLOW = "operating_cash_flow"
    INVESTING_CASH_FLOW = "investing_cash_flow"
    FINANCING_CASH_FLOW = "financing_cash_flow"
    CAPITAL_EXPENDITURE = "capital_expenditure"

    # Key Ratios (from data source)
    ROE = "roe"
    ROA = "roa"
    GROSS_MARGIN = "gross_margin"
    NET_PROFIT_MARGIN = "net_profit_margin"
    CURRENT_RATIO = "current_ratio"
    QUICK_RATIO = "quick_ratio"
    DEBT_RATIO = "debt_ratio"
    ASSET_TURNOVER = "asset_turnover"
    RECEIVABLE_TURNOVER = "receivable_turnover"

    # Market Data
    MARKET_CAP = "market_cap"
    TOTAL_SHARES = "total_shares"
    PE_RATIO = "pe_ratio"
    PB_RATIO = "pb_ratio"
    BASIC_EPS = "basic_eps"
    DILUTED_EPS = "diluted_eps"
    BOOK_VALUE_PER_SHARE = "book_value_per_share"

    @classmethod
    def all(cls) -> frozenset[str]:
        return frozenset(
            v for k, v in vars(cls).items()
            if k.isupper() and not k.startswith("_")
        )


# Freeze IFRSFields
IFRSFields._frozen = True


# =============================================================================
# Source Fields - From data providers
# =============================================================================

class SourceFields:
    """Fields from data providers
    
    These are raw fields that may need transformation.
    """
    
    # Balance Sheet
    GOODWILL = "goodwill"
    INTANGIBLE_ASSETS = "intangible_assets"
    LONG_TERM_INVESTMENT = "long_term_investment"
    CONSTRUCTION_IN_PROGRESS = "construction_in_progress"
    LONG_TERM_DEBT = "long_term_debt"
    SHORT_TERM_DEBT = "short_term_debt"
    SHORT_TERM_BORROWINGS = "short_term_borrowings"
    PARENT_NET_PROFIT = "parent_net_profit"
    NON_CURRENT_LIABILITIES_DUE_1Y = "non_current_liabilities_due_1y"
    BOND_PAYABLE = "bond_payable"
    OTHER_RECEIVABLES = "other_receivables"

    # Income Statement
    INTEREST_EXPENSE = "interest_expense"
    INTEREST_INCOME = "interest_income"
    NON_OPERATING_INCOME = "non_operating_income"
    INVESTMENT_INCOME = "investment_income"
    FAIR_VALUE_CHANGE = "fair_value_change"
    MAIN_BUSINESS_INCOME = "main_business_income"

    # Financial Indicators
    NET_DEBT = "net_debt"
    EBIT = "ebit"
    FREE_CASH_FLOW_TO_FIRM = "free_cash_flow_to_firm"
    FREE_CASH_FLOW_TO_EQUITY = "free_cash_flow_to_equity"
    OCF_TO_SHORT_DEBT = "ocf_to_short_debt"
    DEBT_TO_EQUITY = "debt_to_equity"
    LONG_TERM_DEBT_RATIO = "long_term_debt_ratio"
    CURRENT_ASSETS_RATIO = "current_assets_ratio"
    SELLING_EXPENSE_RATIO = "selling_expense_ratio"
    ADMIN_EXPENSE_RATIO = "admin_expense_ratio"
    FINANCE_EXPENSE_RATIO = "finance_expense_ratio"
    TOTAL_ASSETS_YOY = "total_assets_yoy"
    EQUITY_YOY = "equity_yoy"
    OPERATING_CASH_FLOW_YOY = "operating_cash_flow_yoy"
    CASH_RATIO = "cash_ratio"
    OCF_TO_DEBT = "ocf_to_debt"
    INTEREST_BEARING_DEBT = "interest_bearing_debt"
    EBITDA = "ebitda"
    CURRENTDEBT_TO_DEBT = "currentdebt_to_debt"
    REVENUE_YOY = "revenue_yoy"
    NET_PROFIT_YOY = "net_profit_yoy"

    @classmethod
    def all(cls) -> frozenset[str]:
        return frozenset(
            v for k, v in vars(cls).items()
            if k.isupper() and not k.startswith("_")
        )


# =============================================================================
# All Standard Fields
# =============================================================================

def get_all_standard_fields() -> frozenset[str]:
    """Get all standard fields (IFRS + Source)"""
    return IFRSFields.all() | SourceFields.all()


def get_field_spec(name: str) -> FieldSpec | None:
    """Get field specification by name"""
    return _FIELD_SPECS.get(name)


# Built-in field specs
_FIELD_SPECS: dict[str, FieldSpec] = {
    # IFRS Fields
    "total_assets": FieldSpec(
        name="total_assets",
        type=FieldType.CURRENCY,
        unit="元",
        description="总资产",
        source="ifrs",
    ),
    "total_liabilities": FieldSpec(
        name="total_liabilities",
        type=FieldType.CURRENCY,
        unit="元",
        description="总负债",
        source="ifrs",
    ),
    "total_equity": FieldSpec(
        name="total_equity",
        type=FieldType.CURRENCY,
        unit="元",
        description="股东权益合计",
        source="ifrs",
    ),
    "total_revenue": FieldSpec(
        name="total_revenue",
        type=FieldType.CURRENCY,
        unit="元",
        description="营业总收入",
        source="ifrs",
    ),
    "net_profit": FieldSpec(
        name="net_profit",
        type=FieldType.CURRENCY,
        unit="元",
        description="净利润",
        source="ifrs",
    ),
    "operating_cash_flow": FieldSpec(
        name="operating_cash_flow",
        type=FieldType.CURRENCY,
        unit="元",
        description="经营活动现金流",
        source="ifrs",
    ),
    "market_cap": FieldSpec(
        name="market_cap",
        type=FieldType.CURRENCY,
        unit="元",
        description="总市值",
        source="ifrs",
    ),
    "roe": FieldSpec(
        name="roe",
        type=FieldType.PERCENTAGE,
        unit="%",
        description="净资产收益率",
        source="ifrs",
    ),
    "gross_margin": FieldSpec(
        name="gross_margin",
        type=FieldType.PERCENTAGE,
        unit="%",
        description="毛利率",
        source="ifrs",
    ),
    # Add more as needed...
}


def list_fields(
    source: str | None = None,
    prefix: str | None = None,
) -> list[str]:
    """List all available fields
    
    Args:
        source: Filter by source ("ifrs", "provider", "calculator")
        prefix: Filter by name prefix
    
    Returns:
        List of field names
    """
    fields = list(get_all_standard_fields())
    
    if source:
        def match_source(f: str) -> bool:
            spec = get_field_spec(f)
            return spec is not None and spec.source == source
        fields = [f for f in fields if match_source(f)]
    
    if prefix:
        fields = [f for f in fields if f.startswith(prefix)]
    
    return sorted(fields)
