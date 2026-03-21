# Value Investment Plugin - 开发进展

> 当前进度记录

## 项目结构

```
value-investment-plugin/
├── vi_core/                    # 核心包
│   ├── src/vi_core/
│   │   ├── __init__.py
│   │   ├── spec.py           # pluggy Hook 规范
│   │   ├── fields.py         # 字段类型定义
│   │   └── plugin.py         # pluggy 插件入口 (query 命令实现)
│   └── pyproject.toml
│
├── vi_fields_ifrs/            # IFRS 标准字段插件
│   ├── src/vi_fields_ifrs/
│   │   ├── __init__.py
│   │   └── plugin.py         # 38 个 IFRS 字段
│   └── pyproject.toml
│
├── vi_fields_extension/        # 扩展字段插件
│   ├── src/vi_fields_extension/
│   │   ├── __init__.py       # register_fields() 函数
│   │   └── plugin.py         # pluggy 插件
│   └── pyproject.toml
│
├── provider_tushare/           # ✅ Tushare 数据提供者
│   ├── src/provider_tushare/
│   │   ├── __init__.py
│   │   ├── plugin.py         # pluggy 插件入口
│   │   └── provider.py      # Tushare API 实现 + 字段映射
│   └── pyproject.toml
│
├── calculators/                # ✅ Calculator 插件
│   ├── src/calculators/
│   │   ├── __init__.py
│   │   ├── plugin.py          # pluggy 插件入口
│   │   └── calc_implied_growth.py  # 隐含增长率计算器
│   ├── tests/
│   │   └── test_calc_implied_growth.py  # 10 个测试
│   └── pyproject.toml
│
└── vi_cli/                    # CLI 插件（待实现）
```

## 已完成

### 1. vi_core - 核心框架 ✅

**pluggy Hook 规范 (`spec.py`)：**

```python
# 字段注册
def vi_fields(self) -> dict

# 字段提供者 (FieldProviderSpec)
def vi_markets(self) -> list[str]           # 支持的市场 ["A", "HK", "US"]
def vi_supported_fields(self) -> list[str]  # 支持的字段列表
def vi_fetch_financials(...) -> dict       # 财务报表数据
def vi_fetch_indicators(...) -> dict        # 财务指标
def vi_fetch_market(...) -> dict            # 市场数据

# 计算器
def vi_list_calculators(self) -> list[dict]

# 命令
def vi_commands(self) -> list[str]
def vi_handle(command, args) -> dict
```

**已有命令：**
- `list_fields` - 列出所有可用字段 ✅
- `query` - 查询数据 ✅

### 2. vi_fields_ifrs - IFRS 标准字段 ✅

38 个国际标准字段：
- 资产负债表：total_assets, total_equity, cash_and_equivalents, ...
- 利润表：total_revenue, net_profit, operating_profit, ...
- 现金流量：operating_cash_flow, capital_expenditure, ...
- 比率：roe, roa, gross_margin, pe_ratio, ...

### 3. vi_fields_extension - 扩展字段机制 ✅

**一行代码注册字段：**

```python
from vi_fields_extension import register_fields

register_fields(
    source="my_plugin",
    fields={
        "sector": "所属行业",
        "dividend_yield": "股息率",
    }
)
```

### 4. provider_tushare - Tushare 数据提供者 ✅

**支持的市场：** A 股

**支持的字段（78 个）：**
- 资产负债表（25 个）：total_assets, total_equity, cash_and_equivalents, ...
- 利润表（12 个）：total_revenue, net_profit, operating_profit, ...
- 现金流量表（4 个）：operating_cash_flow, investing_cash_flow, financing_cash_flow
- 财务指标（37 个）：roe, roa, gross_margin, net_profit_margin, ...
- 市场数据（6 个）：market_cap, pe_ratio, pb_ratio, ...

**字段映射机制：**

```python
# provider_tushare/provider.py
FIELD_MAPPINGS: dict[str, dict[str, str]] = {
    "balance_sheet": {
        "total_liab": "total_liabilities",           # Tushare -> 内部标准
        "total_hldr_eqy_exc_min_int": "total_equity",
        "inventories": "inventory",
        "accounts_receiv": "accounts_receivable",
    },
    "indicators": {
        "grossprofit_margin": "gross_margin",         # 注意: Tushare 不同名
        "netprofit_margin": "net_profit_margin",
        "debt_to_assets": "debt_ratio",
    },
    # ...
}
```

## 查询功能 ✅

### 查询流程

```
用户调用
    │
    ▼
vi_handle(command='query', args={...})
    │
    ▼
┌─────────────────────────────────────┐
│         ViCorePlugin._query()      │
│                                     │
│  1. 解析参数 (symbol, fields, years) │
│  2. 分类字段 (financial/indicator/market)
│  3. 调用 provider hooks             │
│  4. 聚合结果                         │
└─────────────────────────────────────┘
    │
    ├──▶ vi_fetch_financials() ──▶ TushareProvider
    │                                  │
    │                              Tushare API (fina_indicator, income, etc.)
    │                              │
    │                              ▼
    │                         应用 FIELD_MAPPINGS
    │                              │
    ├──▶ vi_fetch_indicators() ──────┘
    │
    └──▶ vi_fetch_market() ──────────┘
```

### 使用示例

```python
import pluggy
from vi_core import ValueInvestmentSpecs, plugin as vi_core_plugin
from provider_tushare import plugin as tushare_plugin

# Setup
pm = pluggy.PluginManager('value_investment')
pm.add_hookspecs(ValueInvestmentSpecs)
pm.register(vi_core_plugin, name='vi_core')
pm.register(tushare_plugin, name='tushare')
vi_core_plugin.set_plugin_manager(pm)

# Query
result = pm.hook.vi_handle(
    command='query',
    args={
        'symbol': '600519',      # 贵州茅台
        'fields': 'total_assets,roe,gross_margin,pe_ratio,market_cap',
        'years': 5,
    }
)

# Result
{
  "success": true,
  "data": {
    "symbol": "600519",
    "end_year": 2026,
    "years": 5,
    "data": {
      "total_assets": {2024: 2989亿, 2023: 2727亿, ...},
      "roe": {2024: 38.43, 2023: 36.18, ...},
      "pe_ratio": 20.1,
      "market_cap": 180亿
    }
  }
}
```

### 查询结果示例

**600519 贵州茅台 ROE：**

| 年份 | ROE |
|------|-----|
| 2024 | 38.43% |
| 2023 | 36.18% |
| 2022 | 32.41% |
| 2021 | 29.90% |
| 2020 | 31.41% |

## 安装方式

```bash
# 开发模式
uv pip install -e value-investment-plugin/vi_core
uv pip install -e value-investment-plugin/vi_fields_ifrs
uv pip install -e value-investment-plugin/vi_fields_extension
uv pip install -e value-investment-plugin/provider_tushare

# 环境变量
export TUSHARE_TOKEN=your_token_here
```

## 扩展点设计经验

### 1. entry_points 写法

```toml
# ❌ 错误
[project.entry-points."value_investment.fields"]
extension = "vi_fields_extension:plugin"

# ✅ 正确
[project.entry-points."value_investment.fields"]
extension = "vi_fields_extension.plugin:plugin"
```

需要 `模块名:对象名`，不能只写模块名。

---

### 2. pluggy 的 hook 发现机制

pluggy 通过 `@hookimpl` 装饰器发现 hook 实现，但需要在 **spec 注册之后** 才能正确识别：

```python
pm = pluggy.PluginManager('value_investment')
pm.add_hookspecs(ValueInvestmentSpecs)  # 先注册 spec
pm.register(plugin)                     # 再注册 plugin
```

---

### 3. 模块导入区别

```python
# 导入 __init__.py
from vi_fields_extension import plugin  # ❌ 可能是 module

# 导入 plugin.py 中的对象
from vi_fields_extension.plugin import plugin  # ✅ 正确
```

---

### 4. 扩展点设计原则

**最小代价扩展：**

```python
# 开发者只需一行
register_fields(source="my", fields={...})

# 系统自动聚合
pm.hook.vi_fields()
```

**关键点：**
- 暴露简单 API
- 内部维护注册表
- 通过 pluggy hook 暴露给系统

---

### 5. 分层设计

```
vi_fields_ifrs (冻结)     → 基础标准（不可修改）
vi_fields_extension (扩展) → Provider 字段（可扩展）
provider_tushare          → 数据提供者
vi_core                  → 查询引擎（聚合）
```

职责清晰，易于维护。

---

### 6. 字段映射设计

不同数据源的字段名不同，通过 FIELD_MAPPINGS 统一：

```python
# 用户使用统一的标准字段名
result = pm.hook.vi_handle(command='query', fields='roe, gross_margin')

# Provider 内部映射回原生字段名
FIELD_MAPPINGS = {
    "indicators": {
        "grossprofit_margin": "gross_margin",  # Tushare 原生名 -> 标准名
        "netprofit_margin": "net_profit_margin",
    }
}
```

---

### 7. pyright 类型检查

IDE 类型检查报错 ≠ 代码运行错误。pyright 需要 `extraPaths` 配置，但 IDE 缓存可能导致误报。

```json
{
  "extraPaths": [
    ".venv/lib/python3.12/site-packages",
    "value-investment-plugin/vi_core/src",
    "value-investment-plugin/vi_fields_ifrs/src",
    "value-investment-plugin/vi_fields_extension/src",
    "value-investment-plugin/provider_tushare/src"
  ]
}
```

---

## 下一步

- [x] calculators - ✅ 隐含增长率计算器 (implied_growth)
- [ ] vi_cli - 命令行工具
- [ ] acorn-agent 集成

---

## 5. calculators - 计算器插件 ✅

### 隐含增长率计算器 (implied_growth)

基于 DCF 模型，用市值反推隐含的年化增长率。

**依赖字段：**
- `operating_cash_flow` - 经营现金流（必需）
- `market_cap` - 市值（必需）
- `capital_expenditure` - 资本支出（可选，用于 FCF 计算）
- `free_cash_flow` - 自由现金流（可选，优先使用）

**配置参数：**
```python
{
    "wacc": 0.10,       # 加权平均资本成本 (10%)
    "g_terminal": 0.03, # 永续增长率 (3%)
    "n_years": 10,      # 预测期年数
}
```

**使用示例：**

```python
from calculators.calc_implied_growth import calculate

# 查询数据后
results = {
    "operating_cash_flow": {2024: 100e8, 2023: 90e8},
    "capital_expenditure": {2024: 20e8, 2023: 18e8},
    "market_cap": {2024: 5000e8},
}

implied_growth = calculate(results)
# {2024: 0.1234, 2023: 0.1156}  # 隐含增长率 12.34%, 11.56%
```

**pluggy 集成：**

```python
pm = pluggy.PluginManager('value_investment')
pm.add_hookspecs(ValueInvestmentSpecs)
pm.register(calculators_plugin, name='calculators')

calculators = pm.hook.vi_list_calculators()
# [{name: 'implied_growth', required_fields: [...], ...}]
```
