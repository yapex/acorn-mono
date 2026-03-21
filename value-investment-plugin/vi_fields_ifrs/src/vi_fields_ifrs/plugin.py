"""IFRS Fields Plugin

Provides IFRS (International Financial Reporting Standards) standard fields.
"""
from __future__ import annotations

from typing import Any

from vi_core.spec import vi_hookimpl


# IFRS Standard Fields
IFRS_FIELDS = {
    # Balance Sheet
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
    "adv_receipts",
    "contract_assets",
    "contract_liab",
    # Income Statement
    "total_revenue",
    "net_profit",
    "operating_profit",
    "operating_cost",
    # Cash Flow
    "operating_cash_flow",
    "investing_cash_flow",
    "financing_cash_flow",
    "capital_expenditure",
    # Key Ratios
    "roe",
    "roa",
    "gross_margin",
    "net_profit_margin",
    "current_ratio",
    "quick_ratio",
    "debt_ratio",
    "asset_turnover",
    "receivable_turnover",
    # Market Data
    "market_cap",
    "total_shares",
    "pe_ratio",
    "pb_ratio",
    "basic_eps",
    "diluted_eps",
    "book_value_per_share",
}


class ViFieldsIfrsPlugin:
    """IFRS Fields plugin"""

    @vi_hookimpl
    def vi_fields(self) -> Any:
        """Return IFRS standard fields"""
        return {
            "source": "ifrs",
            "fields": IFRS_FIELDS,
            "description": "International Financial Reporting Standards fields",
        }


plugin = ViFieldsIfrsPlugin()
