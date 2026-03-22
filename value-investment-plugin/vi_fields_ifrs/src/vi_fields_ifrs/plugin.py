"""IFRS Fields Plugin

Provides IFRS (International Financial Reporting Standards) standard fields.
Fields are sourced from standard_fields.py (single source of truth).
"""
from __future__ import annotations

from typing import Any

from vi_core.spec import vi_hookimpl

from vi_fields_extension.standard_fields import IFRS_FIELDS, FIELD_DEFINITIONS


# IFRS 字段描述（从标准定义中提取）
# 格式: {field_name: {description: ...}} 与 _list_fields 期望一致
IFRS_FIELD_DESCRIPTIONS = {
    f: {"description": FIELD_DEFINITIONS[f]["description"]}
    for f in IFRS_FIELDS
    if f in FIELD_DEFINITIONS
}


class ViFieldsIfrsPlugin:
    """IFRS Fields plugin"""

    @vi_hookimpl
    def vi_fields(self) -> Any:
        """Return IFRS standard fields with descriptions"""
        return {
            "source": "ifrs",
            "fields": IFRS_FIELD_DESCRIPTIONS,
            "description": "International Financial Reporting Standards fields",
        }


plugin = ViFieldsIfrsPlugin()
