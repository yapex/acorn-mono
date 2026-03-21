"""Pluggy Hook specifications for Value Investment

Defines the contract between vi_core and Provider/Calculator plugins.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pluggy

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
    ) -> dict[str, dict[int, Any]] | None:
        """Fetch financial statement data (balance sheet, income, cash flow)

        Args:
            symbol: Stock code (e.g. "600519", "00700", "AAPL")
            fields: IFRS standard field names
            end_year: End year
            years: Number of years to fetch

        Returns:
            {field: {year: value}} or None if fields not supported
        """
        return None

    @vi_hookspec
    def vi_fetch_indicators(
        self,
        symbol: str,
        fields: set[str],
        end_year: int,
        years: int = 10,
    ) -> dict[str, dict[int, Any]] | None:
        """Fetch financial indicators (ROE, ROA, gross margin, etc.)

        Args:
            symbol: Stock code
            fields: IFRS standard indicator field names
            end_year: End year
            years: Number of years to fetch

        Returns:
            {field: {year: value}} or None
        """
        return None

    @vi_hookspec
    def vi_fetch_market(
        self,
        symbol: str,
        fields: set[str],
    ) -> dict[str, Any]:
        """Fetch market data (market cap, PE, PB, etc.)

        Args:
            symbol: Stock code
            fields: Market field names (market_cap, pe_ratio, pb_ratio)

        Returns:
            {field: value} single time point values
        """
        return {}


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
        data: dict[str, dict[int, Any]],
        config: dict[str, Any],
    ) -> dict[int, Any] | None:
        """Execute a calculator by name

        Args:
            name: Calculator name (e.g. "implied_growth")
            data: Field data {field: {year: value}}
            config: Calculator-specific config

        Returns:
            {year: value} or None if calculator not found/not implemented
        """
        return None

    @vi_hookspec(firstresult=True)
    def vi_register_calculator(
        self,
        name: str,
        code: str,
        required_fields: list[str],
        description: str = "",
    ) -> dict[str, Any]:
        """Register a calculator dynamically via code string

        Args:
            name: Calculator name
            code: Python code containing calculate(results, config) function
            required_fields: List of required field names
            description: Calculator description

        Returns:
            {"success": bool, "data": {}, "error": str}
        """
        return {"success": False, "error": "Not implemented"}


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
