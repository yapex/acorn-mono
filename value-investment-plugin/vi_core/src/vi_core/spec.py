"""Pluggy Hook specifications for Value Investment

Defines the contract between vi_core and Provider/Calculator plugins.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pandas as pd
import pluggy  # type: ignore[import]

vi_hookspec = pluggy.HookspecMarker("value_investment")
vi_hookimpl = pluggy.HookimplMarker("value_investment")


if TYPE_CHECKING:
    pass


# =============================================================================
# Field Registry Hooks
# =============================================================================

class FieldRegistrySpec:
    """Hook spec for field registry"""

    @vi_hookspec
    def vi_fields(self) -> Any:
        """Return fields provided by this plugin

        Returns:
            {
                "source": str,       # "ifrs", "custom", "provider_name"
                "fields": set,       # Set of field names
                "description": str,   # Description
            }
        """
        return {"source": "", "fields": set(), "description": ""}


# =============================================================================
# Field Provider Hooks
# =============================================================================

class FieldProviderSpec:
    """Hook spec for VI field providers"""

    @vi_hookspec
    def vi_markets(self) -> list[str]:
        """Return list of supported markets

        Returns:
            List of market codes: ["A", "HK", "US"]
        """
        return []

    @vi_hookspec
    def vi_supported_fields(self) -> list[str]:
        """Return list of field names this provider can fetch

        Returns:
            List of field names (e.g. ["total_revenue", "roe"])
        """
        return []

    @vi_hookspec
    def vi_fetch_financials(
        self,
        symbol: str,
        fields: set[str],
        end_year: int,
        years: int = 10,
    ) -> pd.DataFrame | None:
        """Fetch financial statement data (balance sheet, income, cash flow)

        Args:
            symbol: Stock code (e.g. "600519", "00700", "AAPL")
            fields: IFRS standard field names
            end_year: End year
            years: Number of years to fetch

        Returns:
            DataFrame with date column and financial fields, or None
        """
        return None

    @vi_hookspec
    def vi_fetch_indicators(
        self,
        symbol: str,
        fields: set[str],
        end_year: int,
        years: int = 10,
    ) -> pd.DataFrame | None:
        """Fetch financial indicators (ROE, ROA, gross margin, etc.)

        Args:
            symbol: Stock code
            fields: IFRS standard indicator field names
            end_year: End year
            years: Number of years to fetch

        Returns:
            DataFrame with date column and indicator fields, or None
        """
        return None

    @vi_hookspec
    def vi_fetch_market(
        self,
        symbol: str,
        fields: set[str],
    ) -> pd.DataFrame | None:
        """Fetch market data (market cap, PE, PB, etc.)

        Args:
            symbol: Stock code
            fields: Market field names (market_cap, pe_ratio, pb_ratio)

        Returns:
            DataFrame with date column and market fields, or None
        """
        return None

    @vi_hookspec
    def vi_fetch_historical(
        self,
        symbol: str,
        start_date: str | None = None,
        end_date: str | None = None,
        adjust: str = "hfq",
    ) -> pd.DataFrame | None:
        """Fetch historical trading data (OHLCV)

        Args:
            symbol: Stock code (e.g. "600519", "00700", "AAPL")
            start_date: Start date in "YYYY-MM-DD" format (optional)
            end_date: End date in "YYYY-MM-DD" format (optional)
            adjust: Price adjustment method (default: "hfq" 后复权)
                - "": No adjustment (不复权)
                - "qfq": Forward adjustment (前复权)
                - "hfq": Backward adjustment (后复权)

        Returns:
            DataFrame with columns: date, open, high, low, close, volume
            or None if not supported
        """
        return None


# =============================================================================
# Calculator Hooks
# =============================================================================

class CalculatorSpec:
    """Hook spec for VI calculators"""

    @vi_hookspec
    def vi_list_calculators(self) -> list[dict[str, Any]]:
        """Return list of available calculators

        Returns:
            List of calculator specs:
            [{
                "name": "implied_growth",
                "required_fields": ["operating_cash_flow", "market_cap"],
                "description": "...",
            }]
        """
        return []

    @vi_hookspec(firstresult=True)
    def vi_run_calculator(
        self,
        name: str,
        data: pd.DataFrame,
        config: dict[str, Any],
    ) -> pd.Series | None:
        """Execute a calculator by name

        Args:
            name: Calculator name (e.g. "implied_growth")
            data: DataFrame with financial data (index=year, columns=field names)
            config: Calculator-specific config

        Returns:
            pd.Series with year as index, or None if calculator not found
            如果calculator运行时出错，返回:
            {"__error__": True, "calculator": name, "error_type": type, "error_message": msg}
        """
        return None

    @vi_hookspec(firstresult=True)
    def vi_register_calculator(
        self,
        name: str,
        code: str,
        required_fields: list[str],
        namespace: str,
        description: str = "",
    ) -> dict[str, Any] | None:
        """Register a calculator dynamically via code string

        Args:
            name: Calculator name
            code: Python code containing calculate(results, config) function
            required_fields: List of required field names
            namespace: Namespace for the calculator (builtin, user, dynamic)
            description: Calculator description

        Returns:
            {"success": bool, "data": {}, "error": str} or None if not implemented
        """
        return None


# =============================================================================
# Command Handler Hooks
# =============================================================================

class CommandHandlerSpec:
    """Hook spec for VI command handlers"""

    @vi_hookspec
    def vi_commands(self) -> list[str]:
        """Return list of supported commands

        Returns:
            List of command names
        """
        return []

    @vi_hookspec(firstresult=True)
    def vi_handle(self, command: str, args: dict[str, Any]) -> dict[str, Any]:
        """Handle a VI command

        Args:
            command: Command name
            args: Command arguments

        Returns:
            {"success": bool, "data": Any, "error": str}
        """
        return {"success": False, "error": "Not implemented"}


# =============================================================================
# Combined Specs
# =============================================================================

class ValueInvestmentSpecs(
    FieldRegistrySpec,
    FieldProviderSpec,
    CalculatorSpec,
    CommandHandlerSpec,
):
    """Combined hook specifications for Value Investment plugins"""
    pass
