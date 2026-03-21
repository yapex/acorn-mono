"""VI Core Pluggy Plugin

Provides:
- Field registry and specs
- Query engine
- Calculator registry
"""
from __future__ import annotations

from typing import Any, TYPE_CHECKING

from .spec import vi_hookimpl

if TYPE_CHECKING:
    pass


class ViCorePlugin:
    """VI Core plugin for pluggy

    Provides commands for querying financial data.
    """

    # Class-level plugin manager reference
    _pm: Any = None

    @classmethod
    def set_plugin_manager(cls, pm: Any) -> None:
        """Set the plugin manager for field collection"""
        cls._pm = pm

    @vi_hookimpl
    def vi_commands(self) -> list[str]:
        """Return supported commands"""
        return ["list_fields", "query"]

    @vi_hookimpl
    def vi_fields(self) -> Any:
        """Return core fields (empty, fields come from plugins)"""
        return {
            "source": "core",
            "fields": set(),
            "description": "Core - fields defined by plugins",
        }

    @vi_hookimpl
    def vi_handle(self, command: str, args: dict[str, Any]) -> dict[str, Any]:
        """Handle commands"""
        if command == "list_fields":
            return self._list_fields(args)
        elif command == "query":
            return self._query(args)
        return {"success": False, "error": f"Unknown command: {command}"}

    def _list_fields(self, args: dict[str, Any]) -> dict[str, Any]:
        """List all available fields from all plugins"""
        all_fields: dict[str, dict] = {}

        # Collect fields from all plugins via vi_fields hook
        if self._pm:
            for result in self._pm.hook.vi_fields():
                if result:
                    source = result.get("source", "unknown")
                    fields = result.get("fields", set())
                    for field in fields:
                        if field not in all_fields:
                            all_fields[field] = {
                                "source": source,
                                "description": result.get("description", ""),
                            }

        source = args.get("source")
        prefix = args.get("prefix")

        fields = list(all_fields.keys())

        if source:
            fields = [f for f in fields if all_fields[f]["source"] == source]

        if prefix:
            fields = [f for f in fields if f.startswith(prefix)]

        return {
            "success": True,
            "data": {
                "fields": sorted(fields),
                "by_source": {f: all_fields[f]["source"] for f in sorted(fields)},
            }
        }

    def _query(self, args: dict[str, Any]) -> dict[str, Any]:
        """Query financial data from providers

        Args:
            symbol: Stock code (e.g. "600519", "000001")
            fields: Comma-separated field names or "all"
            end_year: End year (default current year)
            years: Number of years to fetch (default 10)
            calculators: Comma-separated calculator names (e.g. "implied_growth")
            calculator_config: Dict of {calculator_name: config_dict}

        Returns:
            {"success": True, "data": {...}}
        """
        symbol = args.get("symbol")
        if not symbol:
            return {"success": False, "error": "Missing required argument: symbol"}

        fields_str = args.get("fields", "")
        end_year = args.get("end_year")
        years = args.get("years", 10)
        calculators_str = args.get("calculators", "")
        calculator_config = args.get("calculator_config", {})

        # Parse end_year
        if end_year is None:
            from datetime import datetime
            end_year = datetime.now().year
        else:
            end_year = int(end_year)
        years = int(years)

        # Parse calculators
        requested_calculators = set(
            c.strip() for c in calculators_str.split(",") if c.strip()
        )

        # Parse fields
        if not self._pm:
            return {"success": False, "error": "Plugin manager not initialized"}

        all_fields: set[str] = set()
        for result in self._pm.hook.vi_supported_fields():
            if result:
                all_fields.update(result)

        if fields_str.lower() == "all":
            fields = all_fields
        else:
            requested = set(f.strip() for f in fields_str.split(",") if f.strip())
            # Filter to supported fields only
            fields = requested & all_fields
            unsupported = requested - all_fields
            if unsupported:
                # Log but continue
                pass

        if not fields and not requested_calculators:
            return {"success": False, "error": "No valid fields specified"}

        # Categorize fields
        indicator_fields = fields & {
            "roe", "roa", "gross_margin", "net_profit_margin",
            "current_ratio", "quick_ratio", "debt_ratio", "asset_turnover",
            "receivable_turnover", "roic", "basic_eps", "diluted_eps",
            "book_value_per_share", "cash_ratio", "ocf_to_debt",
            "interest_bearing_debt", "ebitda", "currentdebt_to_debt",
            "operating_profit_margin", "revenue_yoy", "net_profit_yoy",
        }

        # 市场数据 + 交易数据都通过 vi_fetch_market 获取
        market_fields = fields & {
            "market_cap", "circ_market_cap", "circ_shares", "pe_ratio", "pb_ratio",
            "close", "open", "high", "low", "volume",
        }

        financial_fields = fields - indicator_fields - market_fields

        results: dict[str, Any] = {
            "symbol": symbol,
            "end_year": end_year,
            "years": years,
            "data": {},
        }

        # Fetch from providers
        if financial_fields:
            for result in self._pm.hook.vi_fetch_financials(
                symbol=symbol,
                fields=financial_fields,
                end_year=end_year,
                years=years,
            ):
                if result:
                    results["data"].update(result)

        if indicator_fields:
            for result in self._pm.hook.vi_fetch_indicators(
                symbol=symbol,
                fields=indicator_fields,
                end_year=end_year,
                years=years,
            ):
                if result:
                    results["data"].update(result)

        if market_fields:
            for result in self._pm.hook.vi_fetch_market(
                symbol=symbol,
                fields=market_fields,
            ):
                if result:
                    results["data"].update(result)

        # Run calculators
        if requested_calculators:
            self._run_calculators(results, requested_calculators, calculator_config)

        results["fields_fetched"] = list(results["data"].keys())
        return {"success": True, "data": results}

    def _run_calculators(
        self,
        results: dict[str, Any],
        calculator_names: set[str],
        calculator_config: dict[str, Any],
    ) -> None:
        """Run calculators via hook and add results to data"""
        if not self._pm:
            return

        # Get available calculators
        calc_list = self._pm.hook.vi_list_calculators()
        if not calc_list:
            return

        # Flatten if nested (pluggy returns [[...]])
        if calc_list and isinstance(calc_list[0], list):
            calc_list = calc_list[0]

        # Build calculator registry
        calc_registry: dict[str, dict] = {}
        for calc in calc_list:
            calc_registry[calc["name"]] = calc

        # Run each requested calculator via hook
        for calc_name in calculator_names:
            if calc_name not in calc_registry:
                continue

            calc_spec = calc_registry[calc_name]
            required_fields = set(calc_spec.get("required_fields", []))
            optional_fields = set(calc_spec.get("optional_fields", []))

            # Collect required data
            calc_data: dict[str, dict] = {}
            for field in required_fields | optional_fields:
                if field in results["data"]:
                    calc_data[field] = results["data"][field]

            # Check if all required fields are available
            missing = required_fields - set(calc_data.keys())
            if missing:
                continue  # Skip this calculator

            # Call hook to run calculator (auto-discovery!)
            config = calculator_config.get(calc_name, {})
            calc_result = self._pm.hook.vi_run_calculator(
                name=calc_name,
                data=calc_data,
                config=config,
            )

            if calc_result is None:
                continue  # Calculator not found

            # Check for calculator error
            if isinstance(calc_result, dict) and calc_result.get("__error__"):
                # Calculator运行时出错，记录错误信息
                err_info = f"[{calc_result['calculator']}] {calc_result['error_type']}: {calc_result['error_message']}"
                if "calculator_errors" not in results:
                    results["calculator_errors"] = []
                results["calculator_errors"].append({
                    "calculator": calc_result["calculator"],
                    "error_type": calc_result["error_type"],
                    "error_message": calc_result["error_message"],
                })
                continue  # Skip this calculator, don't add error result

            if calc_result:
                results["data"][calc_name] = calc_result


# Plugin instance for pluggy registration
plugin = ViCorePlugin()
