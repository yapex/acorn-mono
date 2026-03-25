# 字段扩展架构实现计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 实现字段扩展架构，新增 `vi_provide_items` hook，让 Provider 主动协作，支持多 Provider 数据合并与智能路由。

**Architecture:** 
1. 在 `spec.py` 中新增 `vi_provide_items` hook 规范
2. 各 Provider Plugin 实现 `vi_provide_items` 方法，内部进行市场过滤和字段筛选
3. 修改 `QueryEngine._fetch_data` 使用新 hook 替代原有的多个独立 fetch hooks
4. 修改 `plugin.py._query` 使用 `vi_provide_items` 并添加 fallback 机制
5. 保持向后兼容，现有 `vi_fetch_*` hooks 继续可用（通过 fallback 机制）

**重要说明：**
- `daily` 类别（日线 OHLCV 数据：close, open, high, low, volume）暂不支持 `vi_provide_items`，
  通过 `vi_fetch_historical` 获取
- 实现包含 fallback 机制：当 `vi_provide_items` 返回空时，自动回退到 legacy `vi_fetch_*` hooks
- 注意：存在两个代码路径使用 `vi_provide_items`：
  - `QueryEngine._fetch_data` - 用于测试和独立查询
  - `plugin.py._query` - 主命令处理路径，包含 fallback 逻辑

**Tech Stack:** Python, Pluggy, Pandas, pytest

---

## Task 1: 添加 vi_provide_items Hook 规范

**Files:**
- Modify: `value-investment/vi_core/src/vi_core/spec.py`

**Step 1: 在 FieldProviderSpec 中添加 vi_provide_items hook 规范**

在 `FieldProviderSpec` 类中，在 `vi_fetch_historical` 方法之后添加新的 hook 规范：

```python
    @vi_hookspec
    def vi_provide_items(
        self,
        items: list[str],
        symbol: str,
        market: str,
        end_year: int,
        years: int = 10,
    ) -> pd.DataFrame | None:
        """Provider 返回它能提供的 items 数据
        
        统一的字段获取接口，替代 vi_fetch_financials/vi_fetch_indicators/vi_fetch_market。
        Provider 内部根据 items 类型决定从哪个数据源获取。
        
        Args:
            items: 请求的字段列表（标准字段名）
            symbol: 股票代码
            market: 市场代码 (A/HK/US)
            end_year: 结束年份
            years: 查询年数
        
        Returns:
            DataFrame with fiscal_year index and requested fields columns,
            或 None 如果不支持此市场/字段
        """
        return None
```

**Step 2: 运行测试确保无语法错误**

```bash
cd /Users/yapex/workspace/acorn-mono
python -c "from vi_core.spec import FieldProviderSpec; print('OK')"
```

Expected: OK

**Step 3: Commit**

```bash
git add value-investment/vi_core/src/vi_core/spec.py
git commit -m "feat: add vi_provide_items hook spec"
```

---

## Task 2: 在 HK Provider 中实现 vi_provide_items

**Files:**
- Modify: `value-investment/provider_market_hk/src/provider_market_hk/plugin.py`

**Step 1: 在 ProviderHKPlugin 类中添加 vi_provide_items 实现**

在 `vi_fetch_historical` 方法之后添加：

```python
    @vi_hookimpl
    def vi_provide_items(
        self,
        items: list[str],
        symbol: str,
        market: str,
        end_year: int,
        years: int = 10,
    ) -> pd.DataFrame | None:
        """HK Provider 实现 vi_provide_items
        
        只响应 HK 市场的请求，筛选出支持的字段并获取数据。
        """
        # 市场过滤：只响应 HK 市场
        if market != "HK":
            return None
        
        provider = _get_provider()
        
        # 获取 Provider 支持的所有字段
        supported = provider.get_supported_fields()
        
        # 筛选出请求中支持的字段
        available = set(items) & supported
        
        if not available:
            return None
        
        # 分类字段
        financial_fields = set()
        indicator_fields = set()
        market_fields = set()
        
        # 从 FIELD_MAPPINGS 中分类
        for category, mapping in provider.FIELD_MAPPINGS.items():
            category_fields = set(mapping.values())
            if category in ["balance_sheet", "income_statement", "cash_flow"]:
                financial_fields.update(category_fields)
            elif category == "indicators":
                indicator_fields.update(category_fields)
            elif category == "market":
                market_fields.update(category_fields)
        
        # 筛选出各类别中请求的字段
        request_financial = available & financial_fields
        request_indicators = available & indicator_fields
        request_market = available & market_fields
        
        # 收集 DataFrames
        dfs: list[pd.DataFrame] = []
        
        # 获取财务数据
        if request_financial:
            df = provider.fetch_financials(symbol, request_financial, end_year, years)
            if df is not None and not df.empty:
                dfs.append(df)
        
        # 获取指标数据
        if request_indicators:
            df = provider.fetch_indicators(symbol, request_indicators, end_year, years)
            if df is not None and not df.empty:
                dfs.append(df)
        
        # 获取市场数据
        if request_market:
            df = provider.fetch_market(symbol, request_market)
            if df is not None and not df.empty:
                dfs.append(df)
        
        # 合并数据
        if not dfs:
            return None
        
        return self._merge_dfs(dfs)
    
    def _merge_dfs(self, dfs: list[pd.DataFrame]) -> pd.DataFrame | None:
        """合并多个 DataFrame"""
        if not dfs:
            return None
        
        fiscal_year = "fiscal_year"
        result = dfs[0].copy()
        
        # 确保 fiscal_year 是 index
        if fiscal_year in result.columns:
            result = result.set_index(fiscal_year)
        
        for df in dfs[1:]:
            if df is None or df.empty:
                continue
            
            df_to_merge = df.copy()
            if fiscal_year in df_to_merge.columns:
                df_to_merge = df_to_merge.set_index(fiscal_year)
            
            # 找出新列
            cols_to_add = [c for c in df_to_merge.columns if c not in result.columns]
            if not cols_to_add:
                continue
            
            # 单行数据广播
            if len(df_to_merge) == 1:
                for col in cols_to_add:
                    result[col] = df_to_merge[col].iloc[0]
            else:
                result = result.merge(
                    df_to_merge[cols_to_add],
                    left_index=True,
                    right_index=True,
                    how="left"
                )
        
        return result
```

**Step 2: 运行测试确保无语法错误**

```bash
cd /Users/yapex/workspace/acorn-mono
python -c "from provider_market_hk.plugin import ProviderHKPlugin; print('OK')"
```

Expected: OK

**Step 3: Commit**

```bash
git add value-investment/provider_market_hk/src/provider_market_hk/plugin.py
git commit -m "feat: implement vi_provide_items in HK provider"
```

---

## Task 3: 在 US Provider 中实现 vi_provide_items

**Files:**
- Modify: `value-investment/provider_market_us/src/provider_market_us/plugin.py`

**Step 1: 在 ProviderUSPlugin 类中添加 vi_provide_items 实现**

与 HK Provider 类似，但 market 检查为 "US"：

```python
    @vi_hookimpl
    def vi_provide_items(
        self,
        items: list[str],
        symbol: str,
        market: str,
        end_year: int,
        years: int = 10,
    ) -> pd.DataFrame | None:
        """US Provider 实现 vi_provide_items
        
        只响应 US 市场的请求，筛选出支持的字段并获取数据。
        """
        # 市场过滤：只响应 US 市场
        if market != "US":
            return None
        
        provider = _get_provider()
        
        # 获取 Provider 支持的所有字段
        supported = provider.get_supported_fields()
        
        # 筛选出请求中支持的字段
        available = set(items) & supported
        
        if not available:
            return None
        
        # 分类字段
        financial_fields = set()
        indicator_fields = set()
        market_fields = set()
        
        # 从 FIELD_MAPPINGS 中分类
        for category, mapping in provider.FIELD_MAPPINGS.items():
            category_fields = set(mapping.values())
            if category in ["balance_sheet", "income_statement", "cash_flow"]:
                financial_fields.update(category_fields)
            elif category == "indicators":
                indicator_fields.update(category_fields)
            elif category == "market":
                market_fields.update(category_fields)
        
        # 筛选出各类别中请求的字段
        request_financial = available & financial_fields
        request_indicators = available & indicator_fields
        request_market = available & market_fields
        
        # 收集 DataFrames
        dfs: list[pd.DataFrame] = []
        
        # 获取财务数据
        if request_financial:
            df = provider.fetch_financials(symbol, request_financial, end_year, years)
            if df is not None and not df.empty:
                dfs.append(df)
        
        # 获取指标数据
        if request_indicators:
            df = provider.fetch_indicators(symbol, request_indicators, end_year, years)
            if df is not None and not df.empty:
                dfs.append(df)
        
        # 获取市场数据
        if request_market:
            df = provider.fetch_market(symbol, request_market)
            if df is not None and not df.empty:
                dfs.append(df)
        
        # 合并数据
        if not dfs:
            return None
        
        return self._merge_dfs(dfs)
    
    def _merge_dfs(self, dfs: list[pd.DataFrame]) -> pd.DataFrame | None:
        """合并多个 DataFrame"""
        if not dfs:
            return None
        
        fiscal_year = "fiscal_year"
        result = dfs[0].copy()
        
        # 确保 fiscal_year 是 index
        if fiscal_year in result.columns:
            result = result.set_index(fiscal_year)
        
        for df in dfs[1:]:
            if df is None or df.empty:
                continue
            
            df_to_merge = df.copy()
            if fiscal_year in df_to_merge.columns:
                df_to_merge = df_to_merge.set_index(fiscal_year)
            
            # 找出新列
            cols_to_add = [c for c in df_to_merge.columns if c not in result.columns]
            if not cols_to_add:
                continue
            
            # 单行数据广播
            if len(df_to_merge) == 1:
                for col in cols_to_add:
                    result[col] = df_to_merge[col].iloc[0]
            else:
                result = result.merge(
                    df_to_merge[cols_to_add],
                    left_index=True,
                    right_index=True,
                    how="left"
                )
        
        return result
```

**Step 2: 运行测试确保无语法错误**

```bash
cd /Users/yapex/workspace/acorn-mono
python -c "from provider_market_us.plugin import ProviderUSPlugin; print('OK')"
```

Expected: OK

**Step 3: Commit**

```bash
git add value-investment/provider_market_us/src/provider_market_us/plugin.py
git commit -m "feat: implement vi_provide_items in US provider"
```

---

## Task 4: 修改 QueryEngine 使用 vi_provide_items

**Files:**
- Modify: `value-investment/vi_core/src/vi_core/query.py`

**Step 1: 添加 _infer_market 方法**

在 QueryEngine 类中添加市场推断方法（在 `_get_end_year` 方法之后）：

```python
    def _infer_market(self, symbol: str) -> str:
        """从股票代码推断市场
        
        Args:
            symbol: 股票代码
            
        Returns:
            市场代码: "A", "HK", 或 "US"
        """
        # A股：纯数字（6位）
        if symbol.isdigit() and len(symbol) == 6:
            return "A"
        # 港股：以0开头的5位数字（如00700）
        if len(symbol) == 5 and symbol.isdigit():
            return "HK"
        # 美股：字母（如AAPL）
        if symbol.isalpha():
            return "US"
        # 默认尝试HK
        return "HK"
```

**Step 2: 重写 _fetch_data 方法**

替换现有的 `_fetch_data` 方法：

```python
    def _fetch_data(self, symbol: str, items: list[str]) -> dict[str, Any]:
        """获取数据 - 使用 vi_provide_items
        
        通过 pluggy hooks 调用 Provider 获取 Field 数据。
        新的 vi_provide_items hook 让 Provider 主动决定能提供哪些字段。
        
        Args:
            symbol: 股票代码
            items: 可用的 items 列表（排除 Calculator items）
            
        Returns:
            {item: {year: value}} 格式的数据字典
        """
        if not self._pm or not items:
            return {}
        
        # 推断市场
        market = self._infer_market(symbol)
        
        # 计算 end_year
        end_year = self._get_end_year()
        
        # 广播给所有 Provider
        results = self._pm.hook.vi_provide_items(
            items=items,
            symbol=symbol,
            market=market,
            end_year=end_year,
            years=self.years,
        )
        
        # 合并所有 Provider 返回的 DataFrames
        dfs = [r for r in results if r is not None and not r.empty]
        merged_df = self._merge_dfs(dfs)
        
        # 转换为 {field: {year: value}} 格式
        return self._df_to_result_dict(merged_df)
```

**Step 3: 运行测试确保无语法错误**

```bash
cd /Users/yapex/workspace/acorn-mono
python -c "from vi_core.query import QueryEngine; print('OK')"
```

Expected: OK

**Step 4: Commit**

```bash
git add value-investment/vi_core/src/vi_core/query.py
git commit -m "feat: update QueryEngine to use vi_provide_items hook"
```

---

## Task 4B: 在 plugin.py._query 中实现 vi_provide_items 与 fallback

**Files:**
- Modify: `value-investment/vi_core/src/vi_core/plugin.py`

**Step 1: 修改 _query 方法使用 vi_provide_items**

在 `_query` 方法中，添加调用 `vi_provide_items` hook 获取数据的逻辑：

```python
# 使用 vi_provide_items 统一获取数据
dfs: list[pd.DataFrame] = []
for result in self._get_plugin_manager().hook.vi_provide_items(
    items=list(fields),
    symbol=symbol,
    market=market,
    end_year=end_year,
    years=years,
):
    if result is not None and not result.empty:
        dfs.append(result)
```

**Step 2: 实现 fallback 机制**

当 `vi_provide_items` 返回空时，回退到 legacy `vi_fetch_*` hooks：

```python
# Fallback: 如果 vi_provide_items 没有返回数据，尝试旧的 vi_fetch_* hooks
if not dfs:
    # Categorize fields
    indicator_fields = fields & {
        "roe", "roa", "gross_margin", "net_profit_margin",
        "current_ratio", "quick_ratio", "debt_ratio",
        # ... 更多指标字段
    }
    
    market_fields = fields & {
        "market_cap", "circ_market_cap", "pe_ratio", "pb_ratio",
        # ... 更多市场字段
    }
    
    financial_fields = fields - indicator_fields - market_fields
    
    # Fetch from providers using legacy hooks
    if financial_fields:
        for result in self._get_plugin_manager().hook.vi_fetch_financials(
            symbol=symbol,
            fields=financial_fields,
            end_year=end_year,
            years=years,
        ):
            if result is not None and not result.empty:
                dfs.append(result)
    
    if indicator_fields:
        for result in self._get_plugin_manager().hook.vi_fetch_indicators(
            symbol=symbol,
            fields=indicator_fields,
            end_year=end_year,
            years=years,
        ):
            if result is not None and not result.empty:
                dfs.append(result)
    
    if market_fields:
        for result in self._get_plugin_manager().hook.vi_fetch_market(
            symbol=symbol,
            fields=market_fields,
        ):
            if result is not None and not result.empty:
                dfs.append(result)
```

**Step 3: Commit**

```bash
git add value-investment/vi_core/src/vi_core/plugin.py
git commit -m "fix: update _query to use vi_provide_items with fallback"
```

---

## Task 4C: 在 A Provider 中实现 vi_provide_items

**Files:**
- Modify: `value-investment/provider_market_a/src/provider_market_a/plugin.py`

**Step 1: 在 ProviderAPlugin 类中添加 vi_provide_items 实现**

与 HK/US Provider 类似，但 market 检查为 "A"：

```python
    @vi_hookimpl
    def vi_provide_items(
        self,
        items: list[str],
        symbol: str,
        market: str,
        end_year: int,
        years: int = 10,
    ) -> pd.DataFrame | None:
        """A Provider 实现 vi_provide_items
        
        只响应 A 市场的请求，筛选出支持的字段并获取数据。
        """
        # 市场过滤：只响应 A 市场
        if market != "A":
            return None
        
        provider = _get_provider()
        
        # 获取 Provider 支持的所有字段
        supported = provider.get_supported_fields()
        
        # 筛选出请求中支持的字段
        available = set(items) & supported
        
        if not available:
            return None
        
        # 分类字段
        financial_fields = set()
        indicator_fields = set()
        market_fields = set()
        
        # 从 FIELD_MAPPINGS 中分类
        for category, mapping in provider.FIELD_MAPPINGS.items():
            category_fields = set(mapping.values())
            if category in ["balance_sheet", "income_statement", "cash_flow"]:
                financial_fields.update(category_fields)
            elif category == "indicators":
                indicator_fields.update(category_fields)
            elif category == "market":
                market_fields.update(category_fields)
        
        # 筛选出各类别中请求的字段
        request_financial = available & financial_fields
        request_indicators = available & indicator_fields
        request_market = available & market_fields
        
        # 收集 DataFrames
        dfs: list[pd.DataFrame] = []
        
        # 获取财务数据
        if request_financial:
            df = provider.fetch_financials(symbol, request_financial, end_year, years)
            if df is not None and not df.empty:
                dfs.append(df)
        
        # 获取指标数据
        if request_indicators:
            df = provider.fetch_indicators(symbol, request_indicators, end_year, years)
            if df is not None and not df.empty:
                dfs.append(df)
        
        # 获取市场数据
        if request_market:
            df = provider.fetch_market(symbol, request_market)
            if df is not None and not df.empty:
                dfs.append(df)
        
        # 合并数据
        if not dfs:
            return None
        
        return self._merge_dfs(dfs)
    
    def _merge_dfs(self, dfs: list[pd.DataFrame]) -> pd.DataFrame | None:
        """合并多个 DataFrame（与 HK/US Provider 相同）"""
        # ... 与 HK Provider 相同的实现
```

**Step 2: 运行测试确保无语法错误**

```bash
cd /Users/yapex/workspace/acorn-mono
python -c "from provider_market_a.plugin import ProviderAPlugin; print('OK')"
```

Expected: OK

**Step 3: Commit**

```bash
git add value-investment/provider_market_a/src/provider_market_a/plugin.py
git commit -m "feat: implement vi_provide_items in A provider"
```

---

## Task 5: 编写测试验证 vi_provide_items

**Files:**
- Create: `value-investment/vi_core/tests/test_vi_provide_items.py`

**Step 1: 编写测试**

```python
"""Tests for vi_provide_items hook"""
import pandas as pd
import pytest

from vi_core.query import QueryEngine


class MockProvider:
    """Mock Provider for testing"""
    
    def __init__(self, market_code: str, supported_fields: set[str]):
        self.market_code = market_code
        self.supported_fields = supported_fields
    
    def vi_provide_items(self, items, symbol, market, end_year, years):
        """Mock implementation"""
        if market != self.market_code:
            return None
        
        available = set(items) & self.supported_fields
        if not available:
            return None
        
        # 返回模拟数据
        data = {field: [100, 200, 300] for field in available}
        data["fiscal_year"] = [2021, 2022, 2023]
        return pd.DataFrame(data)


class TestViProvideItems:
    """Test vi_provide_items hook"""
    
    def test_market_filtering(self):
        """测试市场过滤 - Provider 只响应自己的市场"""
        # 创建模拟 Provider
        hk_provider = MockProvider("HK", {"net_profit", "roe"})
        us_provider = MockProvider("US", {"net_profit", "roa"})
        
        # HK Provider 应该忽略 US 市场的请求
        result = hk_provider.vi_provide_items(
            items=["net_profit", "roe"],
            symbol="AAPL",
            market="US",
            end_year=2023,
            years=3,
        )
        assert result is None
        
        # US Provider 应该响应 US 市场的请求
        result = us_provider.vi_provide_items(
            items=["net_profit", "roa"],
            symbol="AAPL",
            market="US",
            end_year=2023,
            years=3,
        )
        assert result is not None
        assert "net_profit" in result.columns
    
    def test_field_filtering(self):
        """测试字段过滤 - Provider 只返回支持的字段"""
        provider = MockProvider("HK", {"net_profit", "roe"})
        
        result = provider.vi_provide_items(
            items=["net_profit", "roe", "unsupported_field"],
            symbol="00700",
            market="HK",
            end_year=2023,
            years=3,
        )
        
        assert result is not None
        assert "net_profit" in result.columns
        assert "roe" in result.columns
        assert "unsupported_field" not in result.columns
    
    def test_empty_items_returns_none(self):
        """测试空字段列表返回 None"""
        provider = MockProvider("HK", {"net_profit"})
        
        result = provider.vi_provide_items(
            items=["unsupported_field"],
            symbol="00700",
            market="HK",
            end_year=2023,
            years=3,
        )
        
        assert result is None


class TestQueryEngineMarketInference:
    """Test QueryEngine market inference"""
    
    def test_infer_a_market(self):
        """测试推断 A 股市场"""
        engine = QueryEngine()
        assert engine._infer_market("600519") == "A"
        assert engine._infer_market("000001") == "A"
    
    def test_infer_hk_market(self):
        """测试推断港股市场"""
        engine = QueryEngine()
        assert engine._infer_market("00700") == "HK"
        assert engine._infer_market("09988") == "HK"
    
    def test_infer_us_market(self):
        """测试推断美股市场"""
        engine = QueryEngine()
        assert engine._infer_market("AAPL") == "US"
        assert engine._infer_market("GOOGL") == "US"
```

**Step 2: 运行测试**

```bash
cd /Users/yapex/workspace/acorn-mono/value-investment/vi_core
pytest tests/test_vi_provide_items.py -v
```

Expected: 所有测试通过

**Step 3: Commit**

```bash
git add value-investment/vi_core/tests/test_vi_provide_items.py
git commit -m "test: add tests for vi_provide_items hook"
```

---

## Task 6: 运行集成测试

**Files:**
- Existing: `value-investment/vi_core/tests/test_query.py`

**Step 1: 运行现有测试确保向后兼容**

```bash
cd /Users/yapex/workspace/acorn-mono/value-investment/vi_core
pytest tests/test_query.py -v
```

Expected: 所有测试通过

**Step 2: 运行所有测试**

```bash
cd /Users/yapex/workspace/acorn-mono/value-investment/vi_core
pytest -v
```

Expected: 所有测试通过

**Step 3: Commit（如果有修复）**

```bash
git commit -m "fix: ensure backward compatibility with existing tests"
```

---

## Task 7: 验证文档更新

**Files:**
- Modify: `docs/field-extension-design.md`

**Step 1: 更新待办事项**

在 `docs/field-extension-design.md` 的待办事项部分，将已完成的任务标记为完成：

```markdown
## 7. 待办事项

- [x] 在 `spec.py` 中添加 `vi_provide_items` hook
- [x] 各 Provider 实现 `vi_provide_items` 方法
- [x] 修改 `QueryEngine._fetch_data` 使用新 hook
- [x] 测试验证
```

**Step 2: Commit**

```bash
git add docs/field-extension-design.md
git commit -m "docs: update todo list for field extension"
```

---

## 总结

完成以上任务后，字段扩展架构的核心功能就已经实现：

1. **新增 `vi_provide_items` hook**：统一的字段获取接口
2. **Provider 实现**：HK、US、A Provider 均实现了新方法
3. **QueryEngine 更新**：使用新 hook 获取数据
4. **市场推断**：根据股票代码自动推断市场
5. **测试覆盖**：单元测试和集成测试
6. **Fallback 机制**：确保向后兼容，legacy `vi_fetch_*` hooks 继续可用

**已知限制：**
- `daily` 类别（OHLCV 字段）暂不支持 `vi_provide_items`，通过 `vi_fetch_historical` 获取

**下一步（可选）：**
- 添加更多 Provider 的集成测试
- 实现动态扩展机制（Evolution）
- 优化 `daily` 类别支持
