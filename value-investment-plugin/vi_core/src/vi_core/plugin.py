"""VI Core Pluggy Plugin

Provides:
- Field registry and specs
- Query engine
- Calculator registry
"""
from __future__ import annotations

import sys
from importlib.metadata import entry_points
from typing import Any, TYPE_CHECKING

import pluggy  # type: ignore[import]

from .spec import vi_hookimpl, ValueInvestmentSpecs

if TYPE_CHECKING:
    from acorn_events import EventBus


# Entry point groups for VI sub-plugins
VI_ENTRY_POINT_GROUPS = (
    "value_investment.fields",
    "value_investment.providers",
    "value_investment.calculators",
)


def _get_entry_points(group: str) -> Any:
    """Get entry points by group, compatible with Python 3.9-3.12"""
    try:
        return entry_points(group=group)
    except TypeError:
        eps = entry_points()
        if hasattr(eps, "select"):
            return eps.select(group=group)
        elif isinstance(eps, dict):
            return eps.get(group, [])
        return []


class ViCorePlugin:
    """VI Core plugin for pluggy

    Provides commands for querying financial data.

    Args:
        event_bus: 事件总线实例（IOC: 通过依赖注入获得）
    """

    # Class-level plugin manager reference
    _pm: Any = None

    def __init__(self, event_bus: EventBus | None = None) -> None:
        self._event_bus = event_bus  # IOC: 由外部注入或延迟初始化

    def _get_default_event_bus(self) -> EventBus:
        """获取默认事件总线（延迟导入避免循环依赖）"""
        from acorn_events import EventBus
        return EventBus()

    @classmethod
    def set_plugin_manager(cls, pm: Any) -> None:
        """Set the plugin manager for field collection"""
        cls._pm = pm

    @classmethod
    def _get_plugin_manager(cls) -> Any:
        """Get or create the VI plugin manager"""
        if cls._pm is None:
            cls._pm = cls._create_plugin_manager()
        return cls._pm

    @classmethod
    def _create_plugin_manager(cls) -> Any:
        """Create pluggy plugin manager and discover sub-plugins"""
        pm = pluggy.PluginManager("value_investment")
        pm.add_hookspecs(ValueInvestmentSpecs)

        # Discover and register sub-plugins via entry_points
        for group in VI_ENTRY_POINT_GROUPS:
            for ep in _get_entry_points(group):
                try:
                    pm.register(ep.load(), name=ep.name)
                except Exception as e:
                    print(f"Warning: Failed to load {group}:{ep.name}: {e}", file=sys.stderr)

        return pm

    # =============================================================================
    # Genes Interface (Acorn Core)
    # =============================================================================

    @property
    def commands(self) -> list[str]:
        """Return supported commands for Acorn Core"""
        return ["vi_query", "vi_list_fields", "vi_list_calculators", "vi_register_calculator"]

    def handle(self, task: Any) -> dict[str, Any]:
        """Handle task for Acorn Core"""
        command = task.command
        args = task.args or {}
        return self._handle(command, args)

    @vi_hookimpl
    def vi_commands(self) -> list[str]:
        """Return supported commands"""
        return ["list_fields", "query"]

    @vi_hookimpl
    def vi_fields(self) -> Any:
        """Return core fields (empty, fields come from plugins)"""
        return {
            "source": "core",
            "fields": {},
            "description": "Core - fields defined by plugins",
        }

    @vi_hookimpl
    def vi_handle(self, command: str, args: dict[str, Any]) -> dict[str, Any]:
        """Handle commands via pluggy"""
        return self._handle(command, args)

    def _handle(self, command: str, args: dict[str, Any]) -> dict[str, Any]:
        """Internal command handler"""
        # Strip "vi_" prefix if present
        internal_cmd = command[3:] if command.startswith("vi_") else command

        if internal_cmd == "list_fields":
            return self._list_fields(args)
        elif internal_cmd == "query":
            return self._query(args)
        elif internal_cmd == "list_calculators":
            return self._list_calculators(args)
        elif internal_cmd == "register_calculator":
            return self._register_calculator(args)
        return {"success": False, "error": f"Unknown command: {command}"}

    def _list_fields(self, args: dict[str, Any]) -> dict[str, Any]:
        """List all available fields from all plugins"""
        all_fields: dict[str, dict] = {}

        # Collect fields from all plugins via vi_fields hook
        if self._get_plugin_manager():
            for result in self._get_plugin_manager().hook.vi_fields():
                if result:
                    source = result.get("source", "unknown")
                    fields = result.get("fields", {})
                    # fields 现在是 dict: {field_name: {description: ...}}
                    for field_name, field_info in fields.items():
                        if field_name not in all_fields:
                            all_fields[field_name] = {
                                "source": source,
                                "description": field_info.get("description", ""),
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
                "descriptions": {f: all_fields[f]["description"] for f in sorted(fields)},
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

        # Parse end_year: 智能判断默认值
        # 年报通常在次年 4 月发布
        # 如果当前月份 < 4，使用前年（确保年报已发布）
        # 如果当前月份 >= 4，使用去年
        if end_year is None:
            from datetime import datetime
            now = datetime.now()
            if now.month < 4:
                end_year = now.year - 2  # 去年年报还未发布，用前年
            else:
                end_year = now.year - 1  # 去年年报已发布
        else:
            end_year = int(end_year)
        years = int(years)

        # Parse calculators
        requested_calculators = set(
            c.strip() for c in calculators_str.split(",") if c.strip()
        )

        # Parse fields
        if not self._get_plugin_manager():
            return {"success": False, "error": "Plugin manager not initialized"}

        # 获取系统标准字段（vi_fields hook 返回所有插件定义的字段）
        standard_fields: set[str] = set()
        for result in self._get_plugin_manager().hook.vi_fields():
            if result:
                # vi_fields 返回格式: {field_name: {description: ...}}
                fields_dict = result.get("fields", {})
                standard_fields.update(fields_dict.keys())

        # 获取 Provider 支持的字段（vi_supported_fields hook 返回 Provider 实际能提供的字段）
        provider_fields: set[str] = set()
        for result in self._get_plugin_manager().hook.vi_supported_fields():
            if result:
                provider_fields.update(result)

        if fields_str.lower() == "all":
            requested = standard_fields
            fields = provider_fields
        else:
            requested = set(f.strip() for f in fields_str.split(",") if f.strip())
            # 区分 unsupported 和 unfilled
            # unsupported: 请求的字段不在系统标准字段定义中（系统能力不足）
            # unfilled: 请求的字段在标准字段中，但 Provider 不支持或返回空（Provider 实现问题）
            unsupported = requested - standard_fields  # 系统不知道这个字段
            unfilled = requested & (standard_fields - provider_fields)  # 系统有但 Provider 不支持

            if unsupported:
                event_bus = self._event_bus or self._get_default_event_bus()
                event_bus.publish(
                    "vi.field.unsupported",
                    sender=self,
                    symbol=symbol,
                    fields=list(unsupported),
                )

            if unfilled:
                event_bus = self._event_bus or self._get_default_event_bus()
                event_bus.publish(
                    "vi.field.unfilled",
                    sender=self,
                    symbol=symbol,
                    fields=list(unfilled),
                )

            # 最终使用的字段是请求的字段和 Provider 支持字段的交集
            fields = requested & provider_fields

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
            for result in self._get_plugin_manager().hook.vi_fetch_financials(
                symbol=symbol,
                fields=financial_fields,
                end_year=end_year,
                years=years,
            ):
                if result:
                    results["data"].update(result)

        if indicator_fields:
            for result in self._get_plugin_manager().hook.vi_fetch_indicators(
                symbol=symbol,
                fields=indicator_fields,
                end_year=end_year,
                years=years,
            ):
                if result:
                    results["data"].update(result)

        if market_fields:
            for result in self._get_plugin_manager().hook.vi_fetch_market(
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
        if not self._get_plugin_manager():
            return

        # Get available calculators
        calc_list = self._get_plugin_manager().hook.vi_list_calculators()
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
            calc_result = self._get_plugin_manager().hook.vi_run_calculator(
                name=calc_name,
                data=calc_data,
                config=config,
            )

            if calc_result is None:
                continue  # Calculator not found

            # Check for calculator error
            if isinstance(calc_result, dict) and calc_result.get("__error__"):
                # Calculator运行时出错，记录错误信息
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

    def _list_calculators(self, args: dict[str, Any]) -> dict[str, Any]:
        """List all available calculators"""
        if not self._get_plugin_manager():
            return {"success": False, "error": "Plugin manager not initialized"}

        calc_list = self._get_plugin_manager().hook.vi_list_calculators()
        if not calc_list:
            return {"success": True, "data": {"calculators": []}}

        # Flatten if nested
        if calc_list and isinstance(calc_list[0], list):
            calc_list = calc_list[0]

        return {"success": True, "data": {"calculators": calc_list}}

    def _register_calculator(self, args: dict[str, Any]) -> dict[str, Any]:
        """Register a calculator dynamically"""
        if not self._get_plugin_manager():
            return {"success": False, "error": "Plugin manager not initialized"}

        result = self._get_plugin_manager().hook.vi_register_calculator(
            name=args.get("name"),
            code=args.get("code"),
            required_fields=args.get("required_fields", []),
            description=args.get("description", ""),
            namespace=args.get("namespace", "dynamic"),
        )
        return result if result else {"success": True, "data": {"message": "Calculator registered"}}


    def on_load(self) -> None:
        """Called when plugin is loaded (Genes lifecycle)"""
        # Plugin manager is set by Acorn kernel
        pass

    def on_unload(self) -> None:
        """Called when plugin is unloaded (Genes lifecycle)"""
        pass


# Plugin instance for pluggy registration
plugin = ViCorePlugin()  # type: ignore[assignment]
