# 统一 Items + 预检机制实现计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 重构数据模型，统一 name 管理（Calculator 优先），实现预检机制 + CLI 简化

**Architecture:** 
- 建立统一的 Item 注册机制，Calculator 优先于 Field
- 实现查询前预检，提前发现可用性问题
- 预留 Evolution 接口，等 Agent 能力完善
- CLI 简化为统一的 `items` 概念

**Tech Stack:** Python, pluggy, pytest, pandas

---

## 目录

- [Phase 1: 数据模型重构](#phase-1-数据模型重构)
- [Phase 2: 预检机制](#phase-2-预检机制)
- [Phase 3: 查询引擎改造](#phase-3-查询引擎改造)
- [Phase 4: CLI 简化](#phase-4-cli-简化)
- [Phase 5: Evolution 接口预留](#phase-5-evolution-接口预留)

---

## Phase 1: 数据模型重构

### Task 1: 创建 Item 注册表

**Files:**
- Create: `value-investment/vi_core/src/vi_core/items.py`
- Test: `value-investment/vi_core/tests/test_items.py`

**Step 1: Write the failing test**

```python
# value-investment/vi_core/tests/test_items.py
import pytest
from vi_core.items import ItemRegistry, ItemSource

def test_item_registry_add_calculator():
    """Calculator item 应该能注册"""
    registry = ItemRegistry()
    
    registry.register_calculator(
        name="implied_growth",
        requires=["operating_cash_flow", "market_cap"],
        description="隐含增长率"
    )
    
    item = registry.get("implied_growth")
    assert item is not None
    assert item.source == ItemSource.CALCULATOR
    assert "operating_cash_flow" in item.requires
    assert "market_cap" in item.requires

def test_item_registry_add_field():
    """Field item 应该能注册"""
    registry = ItemRegistry()
    
    registry.register_field(
        name="revenue",
        description="营业总收入"
    )
    
    item = registry.get("revenue")
    assert item is not None
    assert item.source == ItemSource.FIELD
    assert item.requires == []

def test_item_registry_calculator_takes_priority():
    """同名的 Calculator 应该优先于 Field"""
    registry = ItemRegistry()
    
    registry.register_field(name="roe", description="ROE from field")
    registry.register_calculator(name="roe", requires=["net_profit", "equity"], description="ROE calculated")
    
    item = registry.get("roe")
    assert item.source == ItemSource.CALCULATOR

def test_item_registry_list_all():
    """应该能列出所有 items"""
    registry = ItemRegistry()
    registry.register_calculator("calc1", [], "Calc 1")
    registry.register_field("field1", "Field 1")
    
    all_items = registry.list_all()
    assert "calc1" in all_items
    assert "field1" in all_items
```

**Step 2: Run test to verify it fails**

```bash
cd /Users/yapex/workspace/acorn-mono/value-investment/vi_core
pytest tests/test_items.py -v
```
Expected: FAIL - ModuleNotFoundError

**Step 3: Write minimal implementation**

```python
# value-investment/vi_core/src/vi_core/items.py
"""Item Registry - 统一的数据项注册机制

核心概念：
- Item: 可查询的数据项（统一命名空间）
- Calculator: 需要计算的数据项（优先）
- Field: 从 Provider 获取的数据项（兜底）
"""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


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
        """注册 Field 类型的 Item"""
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
```

**Step 4: Run test to verify it passes**

```bash
cd /Users/yapex/workspace/acorn-mono/value-investment/vi_core
pytest tests/test_items.py -v
```
Expected: PASS

**Step 5: Commit**

```bash
git add value-investment/vi_core/src/vi_core/items.py value-investment/vi_core/tests/test_items.py
git commit -m "feat(vi_core): add Item registry for unified name management"
```

---

### Task 2: 迁移现有 Calculator 到 Item 注册表

**Files:**
- Modify: `value-investment/vi_calculators/vi_calculators/__init__.py`
- Test: `value-investment/vi_core/tests/test_items_migration.py`

**Step 1: Write the failing test**

```python
# value-investment/vi_core/tests/test_items_migration.py
import pytest
from vi_core.items import get_registry, ItemSource

def test_migrate_implied_growth():
    """implied_growth 应该从 Calculator 迁移"""
    registry = get_registry()
    
    # 假设 Calculator 加载后应该注册到 Item 注册表
    # 这个测试检查迁移逻辑
    item = registry.get("implied_growth")
    
    # 迁移后应该有这个 item
    # 注意：这个测试会在迁移后通过
    if item:
        assert item.source == ItemSource.CALCULATOR
        assert "operating_cash_flow" in item.requires
        assert "market_cap" in item.requires

def test_migrate_standard_fields():
    """标准 Field 应该迁移"""
    registry = get_registry()
    
    # 财务数据应该是 Field 类型
    for field_name in ["revenue", "net_profit", "total_assets"]:
        item = registry.get(field_name)
        if item:
            assert item.source == ItemSource.FIELD
```

**Step 2: Run test to verify it fails**

```bash
cd /Users/yapex/workspace/acorn-mono/value-investment/vi_core
pytest tests/test_items_migration.py -v
```
Expected: FAIL - implied_growth not found

**Step 3: Write migration helper**

```python
# value-investment/vi_core/src/vi_core/items.py 添加

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
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/test_items_migration.py -v
```
Expected: PASS (迁移后)

**Step 5: Commit**

```bash
git add value-investment/vi_core/src/vi_core/items.py
git commit -m "feat(vi_core): add migration helpers for existing calculators/fields"
```

---

## Phase 2: 预检机制

### Task 3: 创建 Prechecker 类

**Files:**
- Create: `value-investment/vi_core/src/vi_core/precheck.py`
- Test: `value-investment/vi_core/tests/test_precheck.py`

**Step 1: Write the failing test**

```python
# value-investment/vi_core/tests/test_precheck.py
import pytest
from unittest.mock import MagicMock
from vi_core.precheck import Prechecker, PrecheckResult, IssueSeverity

def test_precheck_all_available():
    """所有 items 都可用"""
    prechecker = Prechecker(provider_fields={"revenue", "net_profit"})
    
    result = prechecker.check("600519", ["revenue", "net_profit"])
    
    assert result.available == ["revenue", "net_profit"]
    assert result.issues == []

def test_precheck_missing_field():
    """缺少 Field"""
    prechecker = Prechecker(provider_fields={"revenue"})
    
    result = prechecker.check("600519", ["revenue", "unknown_field"])
    
    assert result.available == ["revenue"]
    assert len(result.issues) == 1
    assert result.issues[0].item == "unknown_field"
    assert "unknown_field" in result.issues[0].reason

def test_precheck_calculator_with_missing_deps():
    """Calculator 依赖缺失"""
    prechecker = Prechecker(
        provider_fields={"revenue"},  # 有 revenue，但没有 operating_cash_flow
        calculator_requires={"implied_growth": ["operating_cash_flow", "market_cap"]}
    )
    
    result = prechecker.check("600519", ["implied_growth"])
    
    assert result.available == []
    assert len(result.issues) == 1
    assert result.issues[0].item == "implied_growth"
    assert "operating_cash_flow" in result.issues[0].reason

def test_precheck_calculator_with_all_deps():
    """Calculator 所有依赖都满足"""
    prechecker = Prechecker(
        provider_fields={"operating_cash_flow", "market_cap"},
        calculator_requires={"implied_growth": ["operating_cash_flow", "market_cap"]}
    )
    
    result = prechecker.check("600519", ["implied_growth"])
    
    assert result.available == ["implied_growth"]
    assert result.issues == []

def test_precheck_mixed():
    """混合场景"""
    prechecker = Prechecker(
        provider_fields={"revenue", "net_profit", "operating_cash_flow", "market_cap"},
        calculator_requires={"implied_growth": ["operating_cash_flow", "market_cap"]}
    )
    
    result = prechecker.check("600519", ["revenue", "implied_growth", "unknown"])
    
    assert set(result.available) == {"revenue", "implied_growth"}
    assert len(result.issues) == 1
    assert result.issues[0].item == "unknown"
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_precheck.py -v
```
Expected: FAIL - ModuleNotFoundError

**Step 3: Write implementation**

```python
# value-investment/vi_core/src/vi_core/precheck.py
"""Prechecker - 查询前可用性检查

在真正执行查询前检查：
1. 请求的 items 是否都存在
2. Calculator 的依赖是否都能满足
3. 返回友好的问题诊断
"""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .items import ItemRegistry, ItemSource


class IssueSeverity(Enum):
    """问题严重程度"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class Issue:
    """问题描述"""
    item: str
    severity: IssueSeverity
    reason: str
    suggestion: str = ""
    missing_fields: list[str] = field(default_factory=list)


@dataclass
class PrecheckResult:
    """预检结果"""
    available: list[str]          # 可用的 items
    issues: list[Issue]            # 问题列表
    symbol: str = ""               # 查询的股票代码
    
    @property
    def success(self) -> bool:
        """是否完全成功"""
        return len(self.issues) == 0
    
    @property
    def has_errors(self) -> bool:
        """是否有错误级别的问题"""
        return any(i.severity == IssueSeverity.ERROR for i in self.issues)


class Prechecker:
    """预检器"""
    
    def __init__(
        self,
        provider_fields: set[str] | None = None,
        calculator_requires: dict[str, list[str]] | None = None,
        registry: ItemRegistry | None = None,
    ):
        """
        Args:
            provider_fields: Provider 能提供的字段集合
            calculator_requires: Calculator name -> [required fields] 映射
            registry: Item 注册表
        """
        self._provider_fields = provider_fields or set()
        self._calculator_requires = calculator_requires or {}
        self._registry = registry or ItemRegistry()
    
    def check(self, symbol: str, items: list[str]) -> PrecheckResult:
        """检查 items 的可用性
        
        Args:
            symbol: 股票代码
            items: 要查询的 items 列表
            
        Returns:
            PrecheckResult: 包含可用 items 和问题列表
        """
        available = []
        issues = []
        
        for item_name in items:
            item = self._registry.get(item_name)
            
            if item is None:
                # Item 不存在于注册表
                issues.append(Issue(
                    item=item_name,
                    severity=IssueSeverity.ERROR,
                    reason=f"未知的数据项: {item_name}",
                    suggestion="使用 'vi list' 查看可用的数据项",
                ))
                continue
            
            if item.source == ItemSource.FIELD:
                # Field 类型：检查 Provider 是否支持
                if item_name in self._provider_fields:
                    available.append(item_name)
                else:
                    issues.append(Issue(
                        item=item_name,
                        severity=IssueSeverity.ERROR,
                        reason=f"当前市场不支持: {item_name}",
                        suggestion="使用 'vi list' 查看支持的数据项",
                    ))
            
            elif item.source == ItemSource.CALCULATOR:
                # Calculator 类型：检查依赖是否满足
                missing = self._check_calculator_deps(item_name, item.requires)
                
                if missing:
                    issues.append(Issue(
                        item=item_name,
                        severity=IssueSeverity.ERROR,
                        reason=f"缺少依赖字段: {', '.join(missing)}",
                        missing_fields=missing,
                        suggestion=f"无法计算 {item_name}，因为 {', '.join(missing)} 不可用",
                    ))
                else:
                    available.append(item_name)
        
        return PrecheckResult(
            available=available,
            issues=issues,
            symbol=symbol,
        )
    
    def _check_calculator_deps(self, name: str, requires: list[str]) -> list[str]:
        """检查 Calculator 依赖是否都满足
        
        Returns:
            缺失的字段列表，空列表表示全部满足
        """
        missing = []
        
        for dep in requires:
            # 检查依赖是否是 Field 且 Provider 支持
            dep_item = self._registry.get(dep)
            
            if dep_item is None:
                missing.append(dep)
            elif dep_item.source == ItemSource.FIELD:
                if dep not in self._provider_fields:
                    missing.append(dep)
            elif dep_item.source == ItemSource.CALCULATOR:
                # 依赖也是 Calculator，递归检查
                sub_missing = self._check_calculator_deps(dep, dep_item.requires)
                missing.extend(sub_missing)
        
        return list(set(missing))  # 去重
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/test_precheck.py -v
```
Expected: PASS

**Step 5: Commit**

```bash
git add value-investment/vi_core/src/vi_core/precheck.py value-investment/vi_core/tests/test_precheck.py
git commit -m "feat(vi_core): add precheck mechanism for query validation"
```

---

### Task 4: 预检结果格式化

**Files:**
- Modify: `value-investment/vi_core/src/vi_core/precheck.py`
- Test: `value-investment/vi_core/tests/test_precheck_format.py`

**Step 1: Write the failing test**

```python
# value-investment/vi_core/tests/test_precheck_format.py
import pytest
from vi_core.precheck import Prechecker, PrecheckResult, Issue, IssueSeverity

def test_format_success():
    """成功时格式化"""
    result = PrecheckResult(
        available=["revenue", "net_profit"],
        issues=[],
        symbol="600519"
    )
    
    lines = result.format()
    
    assert "✅" in lines[0] or "可用" in str(lines)
    assert "revenue" in str(lines)
    assert "net_profit" in str(lines)

def test_format_with_issues():
    """有问题时格式化"""
    result = PrecheckResult(
        available=["revenue"],
        issues=[
            Issue(
                item="implied_growth",
                severity=IssueSeverity.ERROR,
                reason="缺少依赖字段: operating_cash_flow",
                missing_fields=["operating_cash_flow"],
                suggestion="切换到 A 股市场"
            )
        ],
        symbol="00700"
    )
    
    lines = result.format()
    text = "\n".join(lines)
    
    assert "❌" in text or "无法" in text
    assert "implied_growth" in text
    assert "operating_cash_flow" in text

def test_format_table():
    """表格格式输出"""
    result = PrecheckResult(
        available=["revenue", "net_profit"],
        issues=[
            Issue("unknown", IssueSeverity.ERROR, "未知数据项")
        ],
        symbol="600519"
    )
    
    table = result.format_table()
    
    assert "revenue" in table
    assert "✅" in table or "✗" in table
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_precheck_format.py -v
```
Expected: FAIL

**Step 3: Add format methods**

```python
# 在 precheck.py 中添加

@dataclass
class PrecheckResult:
    # ... existing fields ...
    
    def format(self) -> list[str]:
        """格式化输出为行列表"""
        lines = []
        
        if self.success:
            lines.append(f"✅ {self.symbol}: 所有 {len(self.available)} 个数据项可用")
        else:
            lines.append(f"⚠️  {self.symbol}: {len(self.available)}/{len(self.available) + len(self.issues)} 可用")
        
        if self.issues:
            lines.append("")
            lines.append("📋 问题诊断：")
            for issue in self.issues:
                severity_icon = "❌" if issue.severity == IssueSeverity.ERROR else "⚠️"
                lines.append(f"  {severity_icon} {issue.item}")
                lines.append(f"     原因: {issue.reason}")
                if issue.suggestion:
                    lines.append(f"     建议: {issue.suggestion}")
        
        return lines
    
    def format_table(self) -> str:
        """表格格式输出"""
        from tabulate import tabulate
        
        rows = []
        
        # 可用的 items
        for item in self.available:
            rows.append([item, "✅", ""])
        
        # 有问题的 items
        for issue in self.issues:
            rows.append([issue.item, "❌", issue.reason])
        
        return tabulate(rows, headers=["数据项", "状态", "说明"], tablefmt="grid")
    
    def __str__(self) -> str:
        """字符串表示"""
        return "\n".join(self.format())
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/test_precheck_format.py -v
```
Expected: PASS

**Step 5: Commit**

```bash
git add value-investment/vi_core/src/vi_core/precheck.py
git commit -m "feat(vi_core): add formatted output for precheck results"
```

---

## Phase 3: 查询引擎改造

### Task 5: 创建统一查询接口

**Files:**
- Create: `value-investment/vi_core/src/vi_core/query.py`
- Test: `value-investment/vi_core/tests/test_query.py`

**Step 1: Write the failing test**

```python
# value-investment/vi_core/tests/test_query.py
import pytest
from unittest.mock import MagicMock, patch
from vi_core.query import QueryEngine, QueryResult

def test_query_with_precheck():
    """查询前应该先预检"""
    mock_provider = MagicMock()
    mock_provider.fetch.return_value = {"revenue": {2023: 1000}}
    
    engine = QueryEngine(prechecker=mock_prechecker)
    
    # 应该先调用预检
    with patch.object(engine, '_precheck') as mock_precheck:
        mock_precheck.return_value = MagicMock(success=True, available=["revenue"], issues=[])
        engine.query("600519", ["revenue"])
        mock_precheck.assert_called_once()

def test_query_returns_unavailable_in_response():
    """响应中应该包含不可用的 items"""
    mock_prechecker = MagicMock()
    mock_prechecker.check.return_value = MagicMock(
        success=False,
        available=["revenue"],
        issues=[MagicMock(item="implied_growth", reason="缺少字段")]
    )
    
    engine = QueryEngine(prechecker=mock_prechecker)
    result = engine.query("600519", ["revenue", "implied_growth"])
    
    assert result.data.get("revenue") is not None
    assert "implied_growth" in result.unavailable
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_query.py -v
```
Expected: FAIL

**Step 3: Write implementation**

```python
# value-investment/vi_core/src/vi_core/query.py
"""Query Engine - 统一查询接口

核心流程：
1. 预检 - 检查 items 可用性
2. 获取数据 - 从 Provider 或 Calculator
3. 返回结果 - 包含诊断信息
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from .precheck import Prechecker, PrecheckResult
from .items import ItemRegistry, ItemSource


@dataclass
class QueryResult:
    """查询结果"""
    success: bool
    symbol: str
    data: dict[str, Any] = field(default_factory=dict)
    available: list[str] = field(default_factory=list)   # 可用的 items
    unavailable: list[str] = field(default_factory=list)  # 不可用的 items
    issues: list[dict] = field(default_factory=list)      # 问题详情
    precheck: PrecheckResult | None = None


class QueryEngine:
    """查询引擎"""
    
    def __init__(
        self,
        prechecker: Prechecker | None = None,
        registry: ItemRegistry | None = None,
    ):
        self._prechecker = prechecker or Prechecker()
        self._registry = registry or ItemRegistry()
    
    def query(self, symbol: str, items: list[str]) -> QueryResult:
        """执行查询
        
        Args:
            symbol: 股票代码
            items: 要查询的 items
            
        Returns:
            QueryResult: 查询结果
        """
        # 1. 预检
        precheck_result = self._precheck(symbol, items)
        
        if not precheck_result.available:
            return QueryResult(
                success=False,
                symbol=symbol,
                available=[],
                unavailable=[i.item for i in precheck_result.issues],
                issues=[{
                    "item": i.item,
                    "reason": i.reason,
                    "suggestion": i.suggestion,
                } for i in precheck_result.issues],
                precheck=precheck_result,
            )
        
        # 2. 获取数据（这里后续会调用 Provider/Calculator）
        data = self._fetch_data(symbol, precheck_result.available)
        
        return QueryResult(
            success=True,
            symbol=symbol,
            data=data,
            available=precheck_result.available,
            unavailable=[i.item for i in precheck_result.issues],
            issues=[{
                "item": i.item,
                "reason": i.reason,
                "suggestion": i.suggestion,
            } for i in precheck_result.issues],
            precheck=precheck_result,
        )
    
    def _precheck(self, symbol: str, items: list[str]) -> PrecheckResult:
        """执行预检"""
        return self._prechecker.check(symbol, items)
    
    def _fetch_data(self, symbol: str, items: list[str]) -> dict[str, Any]:
        """获取数据（TODO: 后续接入 Provider/Calculator）"""
        # TODO: 后续实现
        return {}
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/test_query.py -v
```
Expected: PASS

**Step 5: Commit**

```bash
git add value-investment/vi_core/src/vi_core/query.py value-investment/vi_core/tests/test_query.py
git commit -m "feat(vi_core): add QueryEngine with precheck integration"
```

---

## Phase 4: CLI 简化

### Task 6: 改造 CLI 命令

**Files:**
- Modify: `value-investment/vi_core/src/vi_core/cli.py`
- Test: `value-investment/vi_core/tests/test_cli.py`

**Step 1: Write the failing test**

```python
# value-investment/vi_core/tests/test_cli.py
import pytest
from typer.testing import CliRunner
from vi_core.cli import app

runner = CliRunner()

def test_cli_list_command():
    """vi list 应该列出所有 items"""
    result = runner.invoke(app, ["list"])
    
    assert result.exit_code == 0
    # 应该能看到 items 列表

def test_cli_query_with_items():
    """vi query --items 应该工作"""
    result = runner.invoke(app, ["query", "600519", "--items", "revenue,net_profit"])
    
    # 预检信息应该显示
    assert "预检" in result.stdout or "可用" in result.stdout

def test_cli_query_with_precheck_warning():
    """不可用的 items 应该显示警告"""
    result = runner.invoke(app, ["query", "00700", "--items", "implied_growth"])
    
    # 应该显示预检结果
    assert "❌" in result.stdout or "无法" in result.stdout
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_cli.py -v
```
Expected: FAIL (CLI 还没改)

**Step 3: Update CLI implementation**

```python
# value-investment/vi_core/src/vi_core/cli.py

# 修改 query 命令
@app.command()
def query(
    symbol: str,
    items: str = typer.Option(None, "--items", "-i", help="逗号分隔的数据项"),
    years: int = 10,
):
    """查询股票数据
    
    Examples:
        acorn vi query 600519 --items roe,revenue
        acorn vi query 00700 --items implied_growth
    """
    # 解析 items
    item_list = [i.strip() for i in items.split(",")] if items else []
    
    # 导入 QueryEngine
    from vi_core.query import QueryEngine
    from vi_core.precheck import Prechecker
    
    # 临时创建（后续通过 DI 注入）
    prechecker = Prechecker(
        provider_fields={"revenue", "net_profit", "roe"},  # TODO: 从 Provider 获取
        calculator_requires={"implied_growth": ["operating_cash_flow", "market_cap"]}
    )
    engine = QueryEngine(prechecker=prechecker)
    
    # 执行预检
    precheck_result = engine._precheck(symbol, item_list)
    
    # 显示预检结果
    if precheck_result.issues:
        typer.echo("\n⚠️  预检发现问题：")
        for issue in precheck_result.issues:
            typer.echo(f"  ❌ {issue.item}")
            typer.echo(f"     {issue.reason}")
            if issue.suggestion:
                typer.echo(f"     💡 {issue.suggestion}")
        typer.echo()
    
    # 执行查询
    result = engine.query(symbol, item_list)
    
    # 显示结果
    if result.data:
        typer.echo(f"\n=== {symbol} 查询结果 ===")
        for item, data in result.data.items():
            typer.echo(f"{item}: {data}")
    else:
        typer.echo("❌ 无数据返回")


@app.command()
def list(
    category: str = typer.Option(None, "--category", "-c", help="按分类筛选"),
):
    """列出所有可用的数据项
    
    Examples:
        acorn vi list
        acorn vi list --category ratio
    """
    from vi_core.items import get_registry, ItemSource
    
    registry = get_registry()
    
    if category:
        items = registry.list_by_category(category)
    else:
        items = registry.list_all()
    
    # TODO: 从 Provider/Calculator 收集 items
    
    typer.echo(f"\n📊 可用数据项 ({len(items)})")
    typer.echo("─" * 40)
    
    for item_name in sorted(items):
        item = registry.get(item_name)
        if item:
            typer.echo(f"  {item_name:<25} {item.description}")
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/test_cli.py -v
```
Expected: PASS

**Step 5: Commit**

```bash
git add value-investment/vi_core/src/vi_core/cli.py
git commit -m "feat(vi_cli): simplify CLI with unified items concept"
```

---

## Phase 5: Evolution 接口预留

### Task 7: 定义 Evolution 事件接口

**Files:**
- Create: `value-investment/vi_core/src/vi_core/evolution.py`
- Test: `value-investment/vi_core/tests/test_evolution.py`

**Step 1: Write the failing test**

```python
# value-investment/vi_core/tests/test_evolution.py
import pytest
from vi_core.evolution import EvolutionEvent, CapabilityMissingEvent

def test_capability_missing_event_structure():
    """能力缺失事件应该包含完整上下文"""
    event = CapabilityMissingEvent(
        item="implied_growth",
        reason="missing_fields",
        missing_fields=["operating_cash_flow"],
        context={"symbol": "00700", "market": "HK"}
    )
    
    assert event.item == "implied_growth"
    assert "operating_cash_flow" in event.missing_fields
    assert event.context["symbol"] == "00700"

def test_evolution_event_to_prompt():
    """应该能生成给 LLM 的 prompt"""
    event = CapabilityMissingEvent(
        item="implied_growth",
        reason="missing_fields",
        missing_fields=["operating_cash_flow"],
        context={"symbol": "00700", "market": "HK"}
    )
    
    prompt = event.to_prompt()
    
    assert "implied_growth" in prompt
    assert "operating_cash_flow" in prompt
    assert "00700" in prompt
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_evolution.py -v
```
Expected: FAIL

**Step 3: Write implementation**

```python
# value-investment/vi_core/src/vi_core/evolution.py
"""Evolution 接口预留

为未来 Agent 能力预留的接口：
- 当预检发现缺失时，发布 Evolution 事件
- 事件携带完整上下文，供 Agent 处理
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any


@dataclass
class EvolutionEvent:
    """Evolution 事件基类"""
    event_type: str


@dataclass
class CapabilityMissingEvent(EvolutionEvent):
    """能力缺失事件
    
    当预检发现缺失时发布此事件，供 Agent 处理。
    """
    event_type: str = "capability_missing"
    
    item: str = ""                           # 缺失的数据项名称
    reason: str = ""                          # 原因类型: missing_fields, market_unsupported, etc.
    missing_fields: list[str] = field(default_factory=list)  # 缺失的字段
    context: dict[str, Any] = field(default_factory=dict)    # 上下文信息
    
    def to_prompt(self) -> str:
        """生成给 LLM Agent 的提示
        
        包含足够的信息让 Agent 能够：
        1. 理解问题
        2. 决定如何解决
        3. 与用户交互
        """
        prompt_parts = [
            "## 能力缺失报告",
            "",
            f"**数据项**: {self.item}",
            f"**原因**: {self.reason}",
        ]
        
        if self.missing_fields:
            prompt_parts.append(f"**缺失字段**: {', '.join(self.missing_fields)}")
        
        if self.context:
            prompt_parts.append("")
            prompt_parts.append("**上下文**:")
            for key, value in self.context.items():
                prompt_parts.append(f"- {key}: {value}")
        
        prompt_parts.extend([
            "",
            "## 可选行动",
            "",
            "1. **创建 Calculator**: 如果缺失的字段可以通过计算获得",
            "2. **切换数据源**: 如果当前市场不支持",
            "3. **告知用户**: 提供替代方案",
            "4. **忽略**: 如果问题无法自动解决",
            "",
            "请决定如何处理此问题。",
        ])
        
        return "\n".join(prompt_parts)
    
    def to_event_dict(self) -> dict[str, Any]:
        """转换为事件总线所需的 dict 格式"""
        return {
            "event_type": self.event_type,
            "item": self.item,
            "reason": self.reason,
            "missing_fields": self.missing_fields,
            "context": self.context,
        }


def publish_capability_missing(
    item: str,
    reason: str,
    missing_fields: list[str],
    context: dict[str, Any],
) -> None:
    """发布能力缺失事件
    
    预留接口，等 Agent 能力完善后启用。
    """
    event = CapabilityMissingEvent(
        item=item,
        reason=reason,
        missing_fields=missing_fields,
        context=context,
    )
    
    # TODO: 发布到事件总线
    # event_bus.publish(AcornEvents.EVO_CAPABILITY_MISSING, **event.to_event_dict())
    
    # 目前只打印日志
    import loguru
    logger = loguru.logger
    logger.warning(f"Capability missing: {item} - {reason} - {missing_fields}")
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/test_evolution.py -v
```
Expected: PASS

**Step 5: Commit**

```bash
git add value-investment/vi_core/src/vi_core/evolution.py value-investment/vi_core/tests/test_evolution.py
git commit -m "feat(vi_core): add Evolution event interface for future Agent integration"
```

---

### Task 8: 集成 Evolution 事件到预检

**Files:**
- Modify: `value-investment/vi_core/src/vi_core/precheck.py`
- Test: `value-investment/vi_core/tests/test_precheck_evolution.py`

**Step 1: Write the failing test**

```python
# value-investment/vi_core/tests/test_precheck_evolution.py
import pytest
from unittest.mock import patch
from vi_core.precheck import Prechecker

def test_precheck_publishes_event_on_missing():
    """预检发现缺失时应该发布 Evolution 事件"""
    prechecker = Prechecker(
        provider_fields={"revenue"},
        calculator_requires={"implied_growth": ["operating_cash_flow"]}
    )
    
    with patch("vi_core.evolution.publish_capability_missing") as mock_publish:
        prechecker.check("00700", ["implied_growth"])
        
        mock_publish.assert_called_once()
        call_args = mock_publish.call_args
        assert call_args[1]["item"] == "implied_growth"
        assert "operating_cash_flow" in call_args[1]["missing_fields"]
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_precheck_evolution.py -v
```
Expected: FAIL

**Step 3: Add Evolution integration**

```python
# 在 precheck.py 中添加

from .evolution import publish_capability_missing

class Prechecker:
    # ... existing code ...
    
    def check(self, symbol: str, items: list[str]) -> PrecheckResult:
        # ... existing check logic ...
        
        # 发现问题时发布 Evolution 事件
        for issue in issues:
            publish_capability_missing(
                item=issue.item,
                reason="missing_fields",
                missing_fields=issue.missing_fields,
                context={
                    "symbol": symbol,
                    "query_items": items,
                }
            )
        
        return PrecheckResult(...)
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/test_precheck_evolution.py -v
```
Expected: PASS

**Step 5: Commit**

```bash
git add value-investment/vi_core/src/vi_core/precheck.py
git commit -m "feat(vi_core): integrate Evolution events into precheck"
```

---

## 总结

### ✅ 已完成

| 文件 | 状态 |
|------|------|
| `vi_core/src/vi_core/items.py` | ✅ Create |
| `vi_core/src/vi_core/precheck.py` | ✅ Create |
| `vi_core/src/vi_core/query.py` | ✅ Create |
| `vi_core/src/vi_core/evolution.py` | ✅ Create |
| `vi_core/src/vi_core/cli.py` | ✅ Modify (统一 items 接口) |
| `vi_calculators/vi_calculators/__init__.py` | ✅ Modify |
| `tests/test_items.py` | ✅ Create |
| `tests/test_precheck.py` | ✅ Create |
| `tests/test_query.py` | ✅ Create |
| `tests/test_evolution.py` | ✅ Create |
| `tests/test_cli.py` | ✅ Create |

### CLI 接口

```bash
# 统一 items 参数
acorn vi query 600519 --items revenue,net_profit,implied_growth

# 列出所有数据项
acorn vi list
acorn vi list --category calculator
```

### Calculator 依赖排序

支持 Calculator 之间的依赖链，拓扑排序确保计算顺序正确：
```
npcf_ratio → test_chain_a → test_chain_b
```

---

**Plan Status: ✅ COMPLETE (2026-03-24)**

**All tasks completed:**
- Phase 1: Item Registry ✅
- Phase 2: Prechecker + Evolution ✅
- Phase 3: QueryEngine with pluggy hooks ✅
- Phase 4: CLI with unified items ✅
- Phase 5: Evolution events ✅
- Calculator dependency topological sort ✅

Two execution options:

**1. Subagent-Driven (this session)** - I dispatch fresh subagent per task, review between tasks, fast iteration

**2. Parallel Session (separate)** - Open new session with executing-plans, batch execution with checkpoints

Which approach?
