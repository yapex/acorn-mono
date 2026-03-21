"""Extension Fields Plugin

Aggregates all extension fields registered via register_fields().
"""
from __future__ import annotations

from typing import Any

from vi_core.spec import hookimpl

from . import get_fields, get_descriptions


class ViFieldsExtensionPlugin:
    """Extension Fields aggregator plugin"""

    @hookimpl
    def vi_fields(self) -> Any:
        """Return all extension fields from registry"""
        all_fields = get_fields()
        all_descriptions = get_descriptions()

        if not all_fields:
            return {
                "source": "extension",
                "fields": set(),
                "description": "Extension fields - use register_fields() to add",
            }

        # Merge all fields
        merged_fields = set()
        descriptions = {}
        for source, fields in all_fields.items():
            merged_fields.update(fields)
            if source in all_descriptions:
                descriptions.update(all_descriptions[source])

        return {
            "source": "extension",
            "fields": merged_fields,
            "description": f"Extension fields from {len(all_fields)} sources",
            "_descriptions": descriptions,
        }


plugin = ViFieldsExtensionPlugin()
