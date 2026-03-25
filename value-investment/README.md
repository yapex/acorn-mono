# Value Investment Plugin

基于 Pluggy 的价值投资分析插件系统，为 Acorn 提供财务数据查询和计算能力。

## 架构概览

```
┌─────────────────────────────────────────────────────────────────┐
│                          vi_core                                 │
│                    (核心插件 + Plugin Manager)                   │
│                                                                 │
│  Commands: vi_query, vi_list, vi_list_calculators              │
│  Hooks: vi_provide_items*, vi_fetch_*, vi_fields, vi_calculators│
│  Entry Points: value_investment.{fields,providers,calculators}   │
└───────────────────────────┬─────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
        ▼                   ▼                   ▼
┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│    Fields     │   │   Providers   │   │  Calculators  │
├───────────────┤   ├───────────────┤   ├───────────────┤
│ vi_fields_ifrs│   │provider_market_a│   │vi_calculators │
│vi_fields_ext  │   │provider_market_hk│  │               │
│ (第三方扩展)   │   │provider_market_us │  │ (第三方扩展)   │
└───────────────┘   └───────────────┘   └───────────────┘
```

### 数据获取流程

```
用户查询 (items: net_profit, roe, market_cap)
         │
         ▼
┌─────────────────────────┐
│  1. Precheck 预检        │
│  - 检查 items 是否存在    │
│  - 检查依赖是否满足       │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│  2. vi_provide_items*   │ ← 新接口：Provider 主动协作
│  - 市场过滤 (A/HK/US)    │
│  - 字段筛选              │
│  - 多 Provider 数据合并   │
└───────────┬─────────────┘
            │ (如果返回空)
            ▼
┌─────────────────────────┐
│  3. Fallback 机制        │ ← 向后兼容
│  - vi_fetch_financials  │
│  - vi_fetch_indicators  │
│  - vi_fetch_market      │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│  4. 运行 Calculator      │
│  - 拓扑排序依赖          │
│  - 逐步计算               │
└───────────┬─────────────┘
            │
            ▼
      返回结果
```

> **注意**：`vi_provide_items` 是新架构的核心 Hook，推荐 Provider 实现此接口。旧版 `vi_fetch_*` hooks 通过 fallback 机制继续支持。

## 子项目

| 项目 | 职责 | 文档 |
|------|------|------|
| [vi_core](./vi_core/README.md) | 核心 Hook Spec + 查询引擎 + BaseDataProvider | [README](./vi_core/README.md) |
| [vi_fields_extension](./vi_fields_extension/README.md) | 字段定义 + StandardFields 常量 | [README](./vi_fields_extension/README.md) |
| [vi_fields_ifrs](./vi_fields_ifrs/README.md) | IFRS 标准字段插件 | [README](./vi_fields_ifrs/README.md) |
| [vi_calculators](./vi_calculators/README.md) | 计算器加载器插件 | [README](./vi_calculators/README.md) |
| [provider_market_a](./provider_market_a/README.md) | A 股数据提供者 (Tushare) | [README](./provider_market_a/README.md) |
| [provider_market_hk](./provider_market_hk/README.md) | 港股数据提供者 (AKShare) | [README](./provider_market_hk/README.md) |
| [calculators](./calculators/README.md) | 内置计算器脚本 | [README](./calculators/README.md) |

## 快速开始

### 安装

```bash
# 使用 uv 安装
cd value-investment-plugin
uv sync
```

### 配置 API Token

```bash
# A 股 (Tushare)
export TUSHARE_TOKEN="your_token_here"
```

### CLI 使用

**注意：** `acorn vi` CLI 已移除，请使用 Python API 或 `acorn run` 直接调用：

```bash
# 通过 Python API
python -c "
from acorn_cli.client import AcornClient
client = AcornClient()
result = client.execute('vi_query', {'symbol': '600519', 'items': 'revenue,net_profit'})
print(result['data'])
"

# 或通过 acorn run（如果支持）
acorn run vi_query --symbol 600519 --items revenue,net_profit
```

### Python API

```python
from acorn_cli.client import AcornClient

client = AcornClient()

# 查询财务数据（统一 items 参数）
result = client.execute("vi_query", {
    "symbol": "600519",
    "items": "revenue,net_profit,market_cap",
    "years": 5,
})
# result = {
#     "success": True,
#     "data": {
#         "symbol": "600519",
#         "end_year": 2024,
#         "years": 5,
#         "data": {
#             "total_revenue": {2024: ..., 2023: ..., ...},
#             "net_profit": {2024: ..., 2023: ..., ...},
#             "market_cap": {2024: ..., ...}  # 单点数据广播到多年
#         },
#         "fields_fetched": ["total_revenue", "net_profit", "market_cap"]
#     }
# }

# 查询并计算隐含增长率（items 包含字段和计算器）
result = client.execute("vi_query", {
    "symbol": "600519",
    "items": "operating_cash_flow,market_cap,implied_growth",
})

# 列出所有可用数据项
result = client.execute("vi_list", {})

# 列出所有计算器
result = client.execute("vi_list_calculators", {})
```

### 数据项概念

系统统一使用 **items** 概念，包含两类：

| 类型 | 说明 | 示例 |
|------|------|------|
| **Field** | 从数据源直接获取的字段 | `total_revenue`, `net_profit`, `roe`, `market_cap` |
| **Calculator** | 通过计算得出的指标 | `implied_growth`, `npcf_ratio` |

查询时系统会自动：
1. 区分 Field 和 Calculator
2. 先获取 Field 数据
3. 再运行 Calculator 计算

## 扩展点

### 1. 添加新字段

在 `vi_fields_extension/standard_fields.py` 中添加：

```python
FIELD_DEFINITIONS = {
    # ...
    "new_field": {"description": "新字段", "category": "...", "source": "custom"},
}
```

### 2. 添加新 Provider

#### 2.1 继承 BaseDataProvider 模板类

```python
# my_provider/provider.py
from vi_core import BaseDataProvider
from vi_fields_extension import StandardFields

class MyProvider(BaseDataProvider):
    MARKET_CODE = "XX"
    
    FIELD_MAPPINGS = {
        "balance_sheet": {"api_field": StandardFields.total_assets},
        "income_statement": {...},
        "indicators": {...},
        "market": {...},
    }
    
    def _normalize_symbol(self, symbol: str) -> str:
        # 标准化股票代码
        return symbol
    
    def _fetch_all_financials(self, symbol, start_year, end_year, fields):
        # 调用 API，返回 DataFrame
        return df
    
    def _fetch_indicators_impl(self, symbol, start_year, end_year):
        return df
    
    def _fetch_market_impl(self, symbol):
        return df
```

#### 2.2 实现 Plugin（推荐实现 vi_provide_items）

```python
# my_provider/plugin.py
from vi_core.spec import vi_hookimpl
import pandas as pd
from .provider import MyProvider

class MyProviderPlugin:
    _provider = None
    
    def _get_provider(self):
        if self._provider is None:
            self._provider = MyProvider()
        return self._provider
    
    @vi_hookimpl
    def vi_markets(self):
        return ["XX"]
    
    @vi_hookimpl
    def vi_supported_fields(self):
        return list(MyProvider.get_supported_fields())
    
    @vi_hookimpl
    def vi_provide_items(
        self,
        items: list[str],
        symbol: str,
        market: str,
        end_year: int,
        years: int = 10,
    ) -> pd.DataFrame | None:
        """新接口：Provider 主动协作
        
        1. 市场过滤：只响应自己的市场
        2. 字段筛选：只返回支持的字段
        3. 分类获取：财务/指标/市场数据
        4. 合并返回：统一 DataFrame
        """
        # 市场过滤
        if market != "XX":
            return None
        
        provider = _get_provider()
        supported = provider.get_supported_fields()
        available = set(items) & supported
        
        if not available:
            return None
        
        # 分类字段（从 FIELD_MAPPINGS 动态计算）
        financial_fields = set()
        indicator_fields = set()
        market_fields = set()
        
        for category, mapping in provider.FIELD_MAPPINGS.items():
            category_fields = set(mapping.values())
            if category in ["balance_sheet", "income_statement", "cash_flow"]:
                financial_fields.update(category_fields)
            elif category == "indicators":
                indicator_fields.update(category_fields)
            elif category == "market":
                market_fields.update(category_fields)
        
        # 分别获取
        dfs = []
        if available & financial_fields:
            df = provider.fetch_financials(symbol, available & financial_fields, end_year, years)
            if df is not None and not df.empty:
                dfs.append(df)
        
        if available & indicator_fields:
            df = provider.fetch_indicators(symbol, available & indicator_fields, end_year, years)
            if df is not None and not df.empty:
                dfs.append(df)
        
        if available & market_fields:
            df = provider.fetch_market(symbol, available & market_fields)
            if df is not None and not df.empty:
                dfs.append(df)
        
        if not dfs:
            return None
        
        return self._merge_dfs(dfs)
    
    def _merge_dfs(self, dfs: list[pd.DataFrame]) -> pd.DataFrame | None:
        """合并多个 DataFrame（单行数据广播到多年）"""
        if not dfs:
            return None
        
        fiscal_year = "fiscal_year"
        result = dfs[0].copy()
        
        if fiscal_year in result.columns:
            result = result.set_index(fiscal_year)
        
        for df in dfs[1:]:
            if df is None or df.empty:
                continue
            
            df_to_merge = df.copy()
            if fiscal_year in df_to_merge.columns:
                df_to_merge = df_to_merge.set_index(fiscal_year)
            
            cols_to_add = [c for c in df_to_merge.columns if c not in result.columns]
            if not cols_to_add:
                continue
            
            # 单行数据广播（如 market_cap）
            if len(df_to_merge) == 1:
                for col in cols_to_add:
                    result[col] = df_to_merge[col].iloc[0]
            else:
                result = result.merge(df_to_merge[cols_to_add], left_index=True, right_index=True, how="left")
        
        return result
    
    # 向后兼容：legacy hooks（可选，fallback 机制会用到）
    @vi_hookimpl
    def vi_fetch_financials(self, symbol, fields, end_year, years):
        provider = _get_provider()
        return provider.fetch_financials(symbol, fields, end_year, years)
    
    @vi_hookimpl
    def vi_fetch_indicators(self, symbol, fields, end_year, years):
        provider = _get_provider()
        return provider.fetch_indicators(symbol, fields, end_year, years)
    
    @vi_hookimpl
    def vi_fetch_market(self, symbol, fields):
        provider = _get_provider()
        return provider.fetch_market(symbol, fields)

plugin = MyProviderPlugin()
```

```toml
# pyproject.toml
[project.entry-points."value_investment.providers"]
my_provider = "my_provider:plugin"
```

### 3. 添加新 Calculator

```python
# calculators/calc_my_indicator.py
"""我的指标计算器"""

REQUIRED_FIELDS = ["field_a", "field_b"]

def calculate(results, config=None):
    # 计算逻辑...
    return {2023: 0.15}
```

## 开发规范

### 1. 字段引用

使用 `StandardFields` 常量，避免硬编码：

```python
# ✅ 正确
from vi_fields_extension import StandardFields
FIELD_MAPPINGS = {"balance_sheet": {"api_field": StandardFields.total_assets}}

# ❌ 错误
FIELD_MAPPINGS = {"balance_sheet": {"api_field": "total_assets"}}
```

### 2. vi_provide_items vs vi_fetch_*

| 特性 | vi_provide_items (新) | vi_fetch_* (旧) |
|------|----------------------|-----------------|
| **调用方式** | 统一接口，一次调用获取所有字段 | 多个独立接口 |
| **Provider 协作** | 支持多 Provider 数据合并 | 单个 Provider |
| **市场过滤** | Provider 内部处理 | QueryEngine 处理 |
| **推荐度** | ⭐⭐⭐ 推荐使用 | ⭐ 向后兼容 |

**建议**：新 Provider 优先实现 `vi_provide_items`，同时保留 `vi_fetch_*` hooks 用于 fallback。

### 3. 已知限制

- **daily 字段**（OHLCV：close, open, high, low, volume）暂不支持 `vi_provide_items`，通过 `vi_fetch_historical` 获取
- Fallback 机制将 daily 字段归类为 `market_fields`，但 `vi_fetch_market` 返回单点快照值而非时间序列
- 如需获取历史 OHLCV 数据，请使用 `vi_fetch_historical` hook

### 4. Provider 返回值

Provider 的 `fetch_*` 方法返回 `pd.DataFrame`：

```python
# fetch_financials/indicators/market 返回 DataFrame
# 只包含映射后的标准字段
# 返回的是数据拷贝，与原始数据无关联

def fetch_financials(self, symbol, fields, end_year, years) -> pd.DataFrame | None:
    """返回带字段映射的 DataFrame，index=年份或日期"""
```

### 5. 错误处理

不要抛出异常，通过返回值表示错误：

```python
# ✅ 正确
def vi_fetch_financials(self, symbol, fields, ...):
    try:
        data = api.fetch(symbol)
        return self._process(data)
    except Exception:
        return None

# ❌ 错误
def vi_fetch_financials(self, symbol, fields, ...):
    data = api.fetch(symbol)  # 可能抛出异常
    return self._process(data)
```

## 测试

```bash
# 运行所有测试
pytest

# 运行特定子项目测试
pytest vi_core/tests/
pytest provider_market_a/tests/
pytest provider_market_hk/tests/

# 运行集成测试（需要 API Token）
pytest -m integration
```

## 目录结构

```
value-investment-plugin/
├── vi_core/                    # 核心插件
│   ├── src/vi_core/
│   │   ├── spec.py            # Hook Specs (vi_provide_items, vi_fetch_*)
│   │   ├── plugin.py          # Plugin 实现 + 命令处理
│   │   ├── query.py           # QueryEngine (独立查询引擎)
│   │   ├── precheck.py        # 预检器
│   │   ├── items.py           # Item 注册表
│   │   └── base_provider.py   # Provider 模板基类
│   └── tests/
├── vi_fields_extension/        # 字段定义
│   └── src/vi_fields_extension/
│       ├── __init__.py        # register_fields API
│       ├── standard_fields.py # FIELD_DEFINITIONS
│       └── plugin.py
├── vi_fields_ifrs/             # IFRS 字段
│   └── src/vi_fields_ifrs/
│       └── plugin.py
├── vi_calculators/             # 计算器加载器
│   └── src/vi_calculators/
│       └── __init__.py
├── provider_market_a/          # A 股提供者 (Tushare)
│   └── src/provider_market_a/
│       ├── provider.py        # TushareProvider
│       └── plugin.py          # 实现 vi_provide_items
├── provider_market_hk/         # 港股提供者 (AKShare)
│   └── src/provider_market_hk/
│       ├── provider.py        # HKProvider
│       └── plugin.py          # 实现 vi_provide_items
├── provider_market_us/         # 美股提供者 (AKShare)
│   └── src/provider_market_us/
│       ├── provider.py        # USProvider
│       └── plugin.py          # 实现 vi_provide_items
├── calculators/                # 计算器脚本
│   └── calc_implied_growth.py
├── vi_cli/                     # CLI 工具（已废弃，请使用 acorn run）
├── tests/                      # 集成测试
└── pyproject.toml
```

## 相关文档

- [field-extension-design.md](../../docs/field-extension-design.md) - 字段扩展架构设计
- [plans/2026-03-25-field-extension.md](../../docs/plans/2026-03-25-field-extension.md) - 实现计划
- [vi_core/README.md](./vi_core/README.md) - vi_core 详细文档
- [Pluggy 文档](https://pluggy.readthedocs.io/)
