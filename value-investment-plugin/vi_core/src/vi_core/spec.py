"""Pluggy Hook specifications for Value Investment

Defines the contract between vi_core and Provider/Calculator plugins.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pluggy

hookspec = pluggy.HookspecMarker("value_investment")
hookimpl = pluggy.HookimplMarker("value_investment")


if TYPE_CHECKING:
    pass


# =============================================================================
# Field Registry Hooks
# =============================================================================

class FieldRegistrySpec:
    """Hook spec for field registry"""

    @hookspec
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

    @hookspec
    def vi_markets(self) -> list[str]:
        """Return list of supported markets

        Returns:
            List of market codes: ["A", "HK", "US"]
        """
        return []

    @hookspec
    def vi_provides(self) -> list[str]:
        """Return list of field names this provider can fetch

        Returns:
            List of field names (e.g. ["total_revenue", "roe"])
        """
        return []

    @hookspec
    def vi_fetch(
        self,
        symbol: str,
        field: str,
        years: int = 10,
    ) -> dict[int, float] | None:
        """Fetch a single field for a symbol

        Args:
            symbol: Stock code (e.g. "600519", "00700", "AAPL")
            field: Field name (e.g. "total_revenue", "roe")
            years: Number of years to fetch

        Returns:
            {year: value} or None if not supported
        """
        return None


# =============================================================================
# Calculator Hooks
# =============================================================================

class CalculatorSpec:
    """Hook spec for VI calculators"""

    @hookspec
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


# =============================================================================
# Command Handler Hooks
# =============================================================================

class CommandHandlerSpec:
    """Hook spec for VI command handlers"""

    @hookspec
    def vi_commands(self) -> list[str]:
        """Return list of supported commands

        Returns:
            List of command names
        """
        return []

    @hookspec(firstresult=True)
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
