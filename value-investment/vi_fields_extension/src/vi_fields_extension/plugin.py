"""Extension Fields Plugin

Aggregates all extension fields from built-in custom fields.
Third-party plugins can contribute fields by implementing FieldRegistrySpec.
"""
from __future__ import annotations

from typing import Any

import pluggy

vi_hookimpl = pluggy.HookimplMarker("value_investment")


class FieldRegistrySpec:
    """Hook spec for field registry"""

    @pluggy.HookspecMarker("value_investment")
    def vi_fields(self) -> dict:
        """Return fields provided by this plugin

        Returns:
            {
                "source": str,       # "ifrs", "custom", "provider_name"
                "fields": set,       # Set of field names
                "description": str,   # Description
            }
        """
        return {"source": "", "fields": set(), "description": ""}


from .standard_fields import FIELD_DEFINITIONS


class ViFieldsExtensionPlugin(FieldRegistrySpec):
    """Extension Fields aggregator plugin"""

    @vi_hookimpl
    def vi_fields(self) -> Any:
        """Return all extension fields (built-in)

        This hook is called by vi_core to collect all extension fields.
        """
        # 从 FIELD_DEFINITIONS 构建字段字典
        all_fields: dict[str, dict] = {
            name: {"description": info.get("description", "")}
            for name, info in FIELD_DEFINITIONS.items()
        }

        return {
            "source": "extension",
            "fields": all_fields,
            "description": "Extension fields",
        }


plugin = ViFieldsExtensionPlugin()
