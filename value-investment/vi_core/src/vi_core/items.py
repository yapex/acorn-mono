"""Item Registry - 统一的数据项注册机制

核心概念：
- Item: 可查询的数据项（统一命名空间）
- Calculator: 需要计算的数据项（优先）
- Field: 从 Provider 获取的数据项（兜底）
"""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum


class ItemSource(Enum):
    """数据项来源"""
    CALCULATOR = "calculator"  # 需要计算器计算
    FIELD = "field"           # 从 Provider 获取


@dataclass
class Item:
    """数据项定义"""
    name: str
    description: str
    source: ItemSource
    requires: list[str] = field(default_factory=list)  # 依赖的其他 items
    category: str = "general"  # 分类: market, financial, ratio, analysis


class ItemRegistry:
    """统一的数据项注册表"""

    def __init__(self):
        self._items: dict[str, Item] = {}

    def register_calculator(
        self,
        name: str,
        requires: list[str],
        description: str = "",
        category: str = "analysis"
    ) -> None:
        """注册 Calculator 类型的 Item"""
        self._items[name] = Item(
            name=name,
            description=description,
            source=ItemSource.CALCULATOR,
            requires=requires,
            category=category,
        )

    def register_field(
        self,
        name: str,
        description: str = "",
        category: str = "financial"
    ) -> None:
        """注册 Field 类型的 Item
        
        只有当 Item 不存在时才注册（Calculator 优先）
        """
        if name not in self._items:
            self._items[name] = Item(
                name=name,
                description=description,
                source=ItemSource.FIELD,
                category=category,
            )

    def get(self, name: str) -> Item | None:
        """获取 Item"""
        return self._items.get(name)

    def list_all(self) -> list[str]:
        """列出所有 Item 名称"""
        return list(self._items.keys())

    def list_by_source(self, source: ItemSource) -> list[str]:
        """按来源列出 Items"""
        return [name for name, item in self._items.items()
                if item.source == source]

    def list_by_category(self, category: str) -> list[str]:
        """按分类列出 Items"""
        return [name for name, item in self._items.items()
                if item.category == category]


# 全局注册表实例
_global_registry: ItemRegistry | None = None


def get_registry() -> ItemRegistry:
    """获取全局注册表"""
    global _global_registry
    if _global_registry is None:
        _global_registry = ItemRegistry()
    return _global_registry


def register_calculator(
    name: str,
    requires: list[str],
    description: str = "",
    category: str = "analysis"
) -> None:
    """注册 Calculator Item"""
    get_registry().register_calculator(name, requires, description, category)


def register_field(
    name: str,
    description: str = "",
    category: str = "financial"
) -> None:
    """注册 Field Item"""
    get_registry().register_field(name, description, category)


def migrate_calculator(name: str, required_fields: list[str], description: str = ""):
    """从 Calculator 规范迁移到 Item 注册表
    
    Calculator 优先，如果同名的 Field 已存在，会被覆盖
    """
    register_calculator(
        name=name,
        requires=required_fields,
        description=description,
    )


def migrate_field(name: str, description: str = "", category: str = "financial"):
    """从 Field 定义迁移到 Item 注册表
    
    只有当 Item 不存在时才注册（Calculator 优先）
    """
    existing = get_registry().get(name)
    if existing is None:
        register_field(name, description, category)
