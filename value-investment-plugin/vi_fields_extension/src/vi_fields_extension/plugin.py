"""Extension Fields Plugin

Aggregates all extension fields from built-in custom fields.
Third-party plugins can contribute fields by implementing FieldRegistrySpec.
"""
from __future__ import annotations

from typing import Any

from vi_core.spec import vi_hookimpl, FieldRegistrySpec

from . import _extension_fields


class ViFieldsExtensionPlugin(FieldRegistrySpec):
    """Extension Fields aggregator plugin"""

    @vi_hookimpl
    def vi_fields(self) -> Any:
        """Return all extension fields (built-in)

        This hook is called by vi_core to collect all extension fields.
        """
        all_fields: dict[str, dict] = {}

        # Built-in custom fields
        for source, fields in _extension_fields.items():
            all_fields.update(fields)

        return {
            "source": "extension",
            "fields": all_fields,
            "description": "Extension fields",
        }


plugin = ViFieldsExtensionPlugin()
