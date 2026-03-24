# vi_core

Value Investment 核心插件，定义 Hook Spec 并提供查询引擎。

## 职责

- 定义所有 Hook Specification（契约）
- 实现 Pluggy Plugin Manager
- 提供 `query`、`list` 命令
- 协调 Provider、Calculator、Fields 插件
- 提供 `BaseDataProvider` 模板基类
- 实现 `QueryEngine` 统一查询接口（预检 + 数据获取 + Calculator 执行）

## QueryEngine

统一查询引擎，负责：
1. **预检** - 检查 items 可用性，提前发现缺失
2. **获取数据** - 通过 pluggy hooks 调用 Provider 获取 Field 数据
3. **运行 Calculator** - 按拓扑排序执行 Calculator（支持依赖链）

### 数据流程

```
QueryEngine.query(symbol, items)
    │
    ├── Prechecker.check() → 预检可用性
    │
    ├── _fetch_data() → 通过 vi_fetch_financials/indicators/market hooks
    │
    └── _run_calculators() → 通过 vi_run_calculator hook
         │
         └── 拓扑排序确保依赖顺序
             e.g., npcf_ratio → test_chain_a → test_chain_b
```

### 查询结果

```python
result = engine.query("600519", ["revenue", "implied_growth"])
# result.data = {
#     "revenue": {2024: 1000, 2023: 900},
#     "implied_growth": {2024: 0.08},
# }
```

## Hook Specs

vi_core 定义了 4 类扩展点：

### 1. FieldRegistrySpec - 字段注册

```python
@vi_hookspec
def vi_fields(self) -> dict:
    """返回插件提供的字段定义

    Returns:
        {
            "source": str,       # 来源标识
            "fields": dict,      # {field_name: {"description": str}}
            "description": str,  # 描述
        }
    """
```

### 2. FieldProviderSpec - 数据提供

```python
@vi_hookspec
def vi_markets(self) -> list[str]:
    """支持的市场列表，如 ["A", "HK", "US"]"""

@vi_hookspec
def vi_supported_fields(self) -> list[str]:
    """能获取的字段列表"""

@vi_hookspec
def vi_fetch_financials(self, symbol, fields, end_year, years) -> dict | None:
    """获取财务报表数据，返回 {field: {year: value}}"""

@vi_hookspec
def vi_fetch_indicators(self, symbol, fields, end_year, years) -> dict | None:
    """获取财务指标，返回 {field: {year: value}}"""

@vi_hookspec
def vi_fetch_market(self, symbol, fields) -> dict:
    """获取市场数据，返回 {field: value}"""

@vi_hookspec
def vi_fetch_historical(self, symbol, start_date, end_date, adjust) -> dict | None:
    """获取历史交易数据，返回 {"date": [...], "open": [...], ...}"""
```

### 3. CalculatorSpec - 计算器

```python
@vi_hookspec
def vi_list_calculators(self) -> list[dict]:
    """返回可用计算器列表"""

@vi_hookspec(firstresult=True)
def vi_run_calculator(self, name, data, config) -> dict | None:
    """执行计算器"""

@vi_hookspec(firstresult=True)
def vi_register_calculator(self, name, code, required_fields, namespace, description) -> dict | None:
    """动态注册计算器"""
```

### 4. CommandHandlerSpec - 命令处理

```python
@vi_hookspec
def vi_commands(self) -> list[str]:
    """支持的命令列表"""

@vi_hookspec(firstresult=True)
def vi_handle(self, command, args) -> dict:
    """处理命令，返回 {"success": bool, "data": Any, "error": str}"""
```

## BaseDataProvider

Provider 模板基类，简化 Provider 开发。

### 特性

- **字段映射**：自动将 API 原始字段映射到系统标准字段
- **数据去重**：按日期去重，保留最新记录
- **过滤字段**：只返回映射后的标准字段
- **模板方法**：子类只需实现 `_fetch_*` 方法

### 使用方式

```python
from vi_core import BaseDataProvider
from vi_fields_extension import StandardFields

class MyProvider(BaseDataProvider):
    MARKET_CODE = "XX"
    
    FIELD_MAPPINGS = {
        "balance_sheet": {"api_field": StandardFields.total_assets},
        "income_statement": {...},
    }
    
    def _normalize_symbol(self, symbol: str) -> str:
        """标准化股票代码"""
        return symbol
    
    def _fetch_all_financials(self, symbol, start_year, end_year, fields) -> pd.DataFrame | None:
        """获取所有财务报表，返回 DataFrame"""
        return df
    
    def _fetch_indicators_impl(self, symbol, start_year, end_year) -> pd.DataFrame | None:
        return df
    
    def _fetch_market_impl(self, symbol) -> pd.DataFrame | None:
        return df
```

### 公共接口

```python
# 获取财务报表
df = provider.fetch_financials("600519", {"total_assets", "roe"}, 2024, 5)

# 获取财务指标
df = provider.fetch_indicators("600519", {"roe", "roa"}, 2024, 5)

# 获取市场数据
df = provider.fetch_market("600519", {"market_cap", "pe_ratio"})
```

### 子类可覆盖方法

| 方法 | 说明 | 默认实现 |
|------|------|----------|
| `_normalize_symbol()` | 标准化股票代码 | 返回原值 |
| `_get_date_column()` | 日期列名 | `"report_date"` |
| `_deduplicate()` | 数据去重 | 按日期去重 |
| `_filter_annual_reports()` | 年报过滤 | 无过滤 |

### 已实现的 Provider

- `provider_market_a` - A 股 (Tushare)
- `provider_market_hk` - 港股 (AKShare)

## 命令

| 命令 | 参数 | 说明 |
|------|------|------|
| `vi_query` | symbol, items?, end_year?, years? | 查询财务数据 |
| `vi_list` | category?, source? | 列出所有可用数据项 |
| `vi_list_calculators` | - | 列出所有计算器 |
| `vi_register_calculator` | name, code, required_fields, description? | 动态注册计算器 |

### CLI 使用

```bash
# 查询财务数据（统一 items 概念，可混合字段和计算器）
acorn vi query 600519 --items revenue,net_profit,implied_growth
acorn vi query 600519 --items operating_cash_flow,market_cap --years 5

# 列出所有数据项（统一视图）
acorn vi list

# 按类型筛选
acorn vi list --category calculator
acorn vi list --category field

# 按来源筛选
acorn vi list --source ifrs

# 列出可用计算器（详细视图）
acorn vi list-calculators
```

### RPC 调用

```bash
echo '{"command": "vi_query", "args": {"symbol": "600519", "fields": "roe"}}' | nc -U ~/.acorn/agent.sock
```

## 插件发现

vi_core 通过 Entry Points 自动发现子插件：

```toml
[project.entry-points."value_investment.fields"]
ifrs = "vi_fields_ifrs.plugin:plugin"

[project.entry-points."value_investment.providers"]
provider_market_a = "provider_market_a.plugin:plugin"
provider_market_hk = "provider_market_hk.plugin:plugin"

[project.entry-points."value_investment.calculators"]
builtin = "vi_calculators.plugin:plugin"
```

## 开发规范

1. **不要直接调用 Provider**：通过 `vi_core` 的命令接口查询数据
2. **使用 StandardFields 常量**：避免硬编码字段名
3. **错误处理**：返回 `{"success": False, "error": "..."}` 而不是抛出异常
4. **Provider 返回 DataFrame**：`fetch_*` 方法返回带字段映射的 DataFrame

## 相关文档

- [字段扩展开发](../vi_fields_extension/README.md)
- [Provider Market A 开发](../provider_market_a/README.md)
- [Provider Market HK 开发](../provider_market_hk/README.md)
- [Calculator 开发](../vi_calculators/README.md)
