"""VI Core Pluggy Plugin

Provides:
- Field registry and specs
- Query engine
- Calculator registry
"""
from __future__ import annotations

from typing import Any, TYPE_CHECKING

from .spec import hookimpl

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

    @hookimpl
    def vi_commands(self) -> list[str]:
        """Return supported commands"""
        return ["list_fields", "query"]

    @hookimpl
    def vi_fields(self) -> Any:
        """Return core fields (empty, fields come from plugins)"""
        return {
            "source": "core",
            "fields": set(),
            "description": "Core - fields defined by plugins",
        }

    @hookimpl
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
        """Query financial data

        Args:
            symbol: Stock code
            fields: Comma-separated field names
            years: Number of years

        Returns:
            {"success": True, "data": DataFrame or dict}
        """
        # TODO: Implement query engine
        return {
            "success": False,
            "error": "Query engine not yet implemented",
        }


# Plugin instance for pluggy registration
plugin = ViCorePlugin()
