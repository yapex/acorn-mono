"""
VI Plugin for Acorn
===================
Bridges vi_core (ValueInvestmentSpecs) to acorn (Genes spec).

Provides commands:
- vi_query: Query financial data for a stock
- vi_list_fields: List all available fields
- vi_list_calculators: List all available calculators
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, TYPE_CHECKING

# Third-party imports (installed via uv)
import pluggy  # type: ignore[import]

# Add plugin paths for local packages (value-investment-plugin workspace)
# This is a temporary workaround for local development. In production,
# these packages should be installed via pip/uv.
_LOCAL_PLUGIN_PATHS = [
    Path(__file__).parent.parent.parent.parent
    / "value-investment-plugin"
    / "vi_core"
    / "src",
    Path(__file__).parent.parent.parent.parent
    / "value-investment-plugin"
    / "vi_fields_ifrs"
    / "src",
    Path(__file__).parent.parent.parent.parent
    / "value-investment-plugin"
    / "vi_fields_extension"
    / "src",
    Path(__file__).parent.parent.parent.parent
    / "value-investment-plugin"
    / "provider_tushare"
    / "src",
    Path(__file__).parent.parent.parent.parent
    / "value-investment-plugin"
    / "calculators",
]

for _p in _LOCAL_PLUGIN_PATHS:
    if str(_p) not in sys.path and _p.exists():
        sys.path.insert(0, str(_p))

# Acorn imports
from acorn_core import Task, hookimpl  # type: ignore[import]

# VI Core imports - these imports will succeed if packages are installed
# or if local paths are added above
try:
    from vi_core import ValueInvestmentSpecs, plugin as vi_core_plugin  # type: ignore[import]
except ImportError:
    # Fallback for when vi_core is not installed
    ValueInvestmentSpecs = None  # type: ignore
    vi_core_plugin = None  # type: ignore


def _get_entry_points(group: str) -> list[Any]:
    """Get entry points by group, compatible with Python 3.9-3.12"""
    from importlib.metadata import entry_points

    try:
        # Python 3.10+
        return list(entry_points(group=group))
    except TypeError:
        # Python 3.9
        eps = entry_points()
        if hasattr(eps, "select"):
            return list(eps.select(group=group))
        elif isinstance(eps, dict):
            return list(eps.get(group, []))
        return []


class VIPlugin:
    """
    VI Plugin bridging to acorn-agent.

    Implements the Genes spec (commands, handle) and delegates
    to vi_core via ValueInvestmentSpecs hooks.
    """

    # Plugin manager for vi_core (shared with CLI)
    _vi_pm: Any = None

    @classmethod
    def _setup_vi_plugin_manager(cls) -> Any:
        """Setup pluggy plugin manager and register all VI plugins"""
        if cls._vi_pm is not None:
            return cls._vi_pm

        if ValueInvestmentSpecs is None or vi_core_plugin is None:
            raise ImportError(
                "vi_core package is not installed. "
                "Install with: uv pip install -e ./value-investment-plugin/vi_core"
            )

        # Import calculator loader
        try:
            from vi_calculators import CalculatorLoaderPlugin  # type: ignore[import]
        except ImportError:
            # Calculator loader not available
            CalculatorLoaderPlugin = None  # type: ignore

        pm = pluggy.PluginManager("value_investment")
        pm.add_hookspecs(ValueInvestmentSpecs)

        # Register core plugin
        pm.register(vi_core_plugin, name="vi_core")

        # Register calculator loader if available
        if CalculatorLoaderPlugin is not None:
            calc_loader = CalculatorLoaderPlugin()
            pm.register(calc_loader, name="calculators")

        # Register providers and fields via entry_points
        _entry_point_configs = [
            ("value_investment.providers", "tushare"),
            ("value_investment.fields", "ifrs"),
            ("value_investment.fields", "extension"),
        ]

        for group, name in _entry_point_configs:
            eps = _get_entry_points(group)
            for ep in eps:
                if ep.name == name:
                    try:
                        plugin_instance = ep.load()
                        pm.register(plugin_instance, name=ep.name)
                    except Exception as e:
                        print(f"Warning: Failed to load {name}: {e}", file=sys.stderr)

        # Set plugin manager for vi_core
        vi_core_plugin.set_plugin_manager(pm)

        cls._vi_pm = pm
        return pm

    @classmethod
    def get_vi_pm(cls) -> Any:
        """Get or create the VI plugin manager"""
        if cls._vi_pm is None:
            return cls._setup_vi_plugin_manager()
        return cls._vi_pm

    @hookimpl
    def commands(self) -> list[str]:
        """Declare supported commands"""
        return [
            "vi_query",
            "vi_list_fields",
            "vi_list_calculators",
            "vi_register_calculator",
        ]

    @hookimpl
    def handle(self, task: Task) -> dict[str, Any]:
        """
        Handle VI commands by delegating to vi_core.

        Args:
            task: Task with command and args

        Returns:
            Result dict with success/data or error
        """
        command = task.command
        args = task.args or {}

        # Get VI plugin manager
        pm = self.get_vi_pm()

        # Map acorn command to vi_core command
        if command == "vi_query":
            vi_command = "query"
        elif command == "vi_list_fields":
            vi_command = "list_fields"
        elif command == "vi_list_calculators":
            return self._list_calculators(args, pm)
        elif command == "vi_register_calculator":
            return self._register_calculator(args, pm)
        else:
            return {
                "success": False,
                "error": {"code": "UNKNOWN_COMMAND", "message": f"Unknown command: {command}"}
            }

        # Delegate to vi_core via vi_handle hook
        result = pm.hook.vi_handle(
            command=vi_command,
            args=args,
        )

        # Handle result (vi_handle returns dict directly)
        if isinstance(result, list):
            # Some hooks return lists, get first non-None
            result = next((r for r in result if r is not None), {"success": False, "error": "No result"})

        return result

    def _list_calculators(self, args: dict, pm: Any) -> dict[str, Any]:
        """List calculators via hook"""
        calcs = pm.hook.vi_list_calculators()

        # Flatten if nested
        if calcs and isinstance(calcs[0], list):
            calcs = calcs[0]

        return {
            "success": True,
            "data": {
                "calculators": calcs or [],
            }
        }

    def _register_calculator(self, args: dict, pm: Any) -> dict[str, Any]:
        """Register a calculator dynamically via code string"""
        name = args.get("name")
        code = args.get("code")
        required_fields = args.get("required_fields", [])
        description = args.get("description", "")
        namespace = args.get("namespace", "dynamic")

        if not name or not code:
            return {
                "success": False,
                "error": {"code": "INVALID_ARGS", "message": "name and code are required"},
            }

        return pm.hook.vi_register_calculator(
            name=name,
            code=code,
            required_fields=required_fields,
            description=description,
            namespace=namespace,
        )

    @hookimpl
    def get_capabilities(self) -> dict[str, Any]:
        """Declare capabilities for this plugin"""
        return {
            "name": "vi",
            "description": "Value Investment - Financial data query and analysis",
            "commands": [
                {
                    "name": "vi_query",
                    "description": "Query financial data for a stock",
                    "args": {
                        "symbol": {"type": "string", "required": True, "description": "Stock symbol (e.g. 600519)"},
                        "fields": {"type": "string", "required": False, "default": "all", "description": "Comma-separated fields"},
                        "years": {"type": "integer", "required": False, "default": 10, "description": "Number of years"},
                        "calculators": {"type": "string", "required": False, "default": "", "description": "Comma-separated calculators"},
                        "calculator_config": {"type": "object", "required": False, "default": {}},
                    }
                },
                {
                    "name": "vi_list_fields",
                    "description": "List all available financial fields",
                    "args": {
                        "source": {"type": "string", "required": False, "description": "Filter by source"},
                        "prefix": {"type": "string", "required": False, "description": "Filter by prefix"},
                    }
                },
                {
                    "name": "vi_list_calculators",
                    "description": "List all available calculators",
                    "args": {}
                },
                {
                    "name": "vi_register_calculator",
                    "description": "Register a calculator dynamically via code string",
                    "args": {
                        "name": {"type": "string", "required": True, "description": "Calculator name"},
                        "code": {"type": "string", "required": True, "description": "Python code with calculate(results, config) function"},
                        "required_fields": {"type": "array", "required": True, "description": "List of required field names"},
                        "description": {"type": "string", "required": False, "default": ""},
                        "namespace": {"type": "string", "required": False, "default": "dynamic", "description": "Namespace: builtin, user, or dynamic"},
                    }
                },
            ],
        }


# Plugin instance for pluggy registration
plugin = VIPlugin()
