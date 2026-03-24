"""VI Fields IFRS - International Standard Fields"""
from vi_fields_ifrs.plugin import plugin, ViFieldsIfrsPlugin
from vi_fields_extension.standard_fields import IFRS_FIELDS

__all__ = [
    "plugin",
    "ViFieldsIfrsPlugin",
    "IFRS_FIELDS",
]
