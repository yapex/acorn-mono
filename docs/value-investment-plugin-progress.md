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
- [x] vi_cli - ✅ 已合并到 acorn-cli，使用 `acorn vi` 命令
- [x] acorn-agent 集成 - ✅ 已合并到 acorn-cli
- [x] 计算器进化机制 - ✅ 实现 EVO_CAPABILITY_MISSING + get_evolution_spec Hook

---

## 7. 计算器进化机制 ✅

### 架构

```
用户请求不存在的计算器
         │
         ▼
┌─────────────────────────────────────────────┐
│  ViCorePlugin._run_calculators()            │
│  → 发现计算器不存在                          │
│  → 发布 EVO_CAPABILITY_MISSING 事件         │
└─────────────────────┬───────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────┐
│  EvoManager._on_capability_missing()       │
│  → 记录能力缺失                             │
│  → 调用 _get_evolution_spec()              │
│  → CalculatorEngine.get_evolution_spec()    │
└─────────────────────┬───────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────┐
│  打印 EVOLUTION_NEEDED + 进化规范           │
└─────────────────────────────────────────────┘
```

### 事件常量

```python
class AcornEvents:
    EVO_CAPABILITY_MISSING = "evo.capability.missing"
    EVO_REQUEST = "evo.request"
    EVO_START = "evo.start"
    EVO_SUCCESS = "evo.success"
    EVO_FAILED = "evo.failed"
```

### Hook 定义

```python
# acorn_core/specs.py
@hookspec(firstresult=True)
def get_evolution_spec(
    capability_type: str,
    name: str,
    context: dict | None = None,
) -> str | None:
    """询问插件是否支持某能力，不支持则返回进化规范"""
```

### 使用方式

```bash
# 请求不存在的计算器，触发进化
acorn vi query 600519 -r "net_profit" -c nonexistent_calculator

# 输出
# ============================================================
# EVOLUTION_NEEDED: calculator/nonexistent_calculator
# ============================================================
# 要创建计算器 `nonexistent_calculator`，请按以下格式提供代码：
# ...
```

---

## 8. acorn-cli 命令行工具 ✅

### 核心命令

```bash
# 插件管理
acorn list                        # 列出已安装插件
acorn install <package>           # 安装插件
acorn uninstall <name>            # 卸载插件

# 配置
acorn config tui                  # TUI 配置界面
acorn config enable <name>        # 启用插件
acorn config disable <name>       # 禁用插件

# 系统状态
acorn status                      # 查看系统状态
```

### VI 命令

```bash
acorn vi query 600519 -r "roe,net_profit" -y 5
acorn vi list-fields
acorn vi list-calculators
```

### HTTP 服务

```bash
# 启动服务
uvicorn acorn_cli.server:app --host 0.0.0.0 --port 8000

# HTTP API
POST /execute {"command": "vi_query", "args": {...}}
GET /status
GET /health
```

---

## 9. 当前项目结构

```
acorn-mono/
├── acorn-core/                    # 核心框架
│   └── src/acorn_core/
│       ├── kernel.py              # Acorn 内核
│       ├── specs.py              # Hook specs (EvolutionSpec)
│       └── plugins/
│           └── evo_manager.py    # 进化管理器
│
├── acorn-cli/                     # CLI 工具
│   └── src/acorn_cli/
│       ├── cli.py                # typer CLI
│       ├── server.py             # FastAPI 服务端
│       ├── client.py             # HTTP 客户端
│       └── registry.py           # 插件注册表
│
├── acorn-events/                  # 事件系统
│   └── src/acorn_events/
│       └── __init__.py           # AcornEvents 常量
│
├── value-investment-plugin/       # VI 领域插件
│   ├── vi_core/                  # 核心包
│   ├── vi_calculators/           # 计算器引擎
│   ├── vi_fields_extension/      # 字段扩展
│   ├── vi_fields_ifrs/          # IFRS 标准字段
│   └── provider_market_a/        # A股数据源
│
└── docs/
    ├── EVOLUTION_DESIGN.md       # 演化机制设计
    ├── value-investment-plugin-design.md  # VI 架构设计
    └── value-investment-plugin-progress.md  # 进度跟踪
```

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

---

## 6. CLI - 命令行工具 ✅

> **注意**: vi_cli 已合并到 acorn-cli。现在使用 `acorn vi` 命令。

### 使用命令

```bash
# 查询数据
acorn vi query 600900 -r "roe,net_profit_margin,pe_ratio,market_cap" -y 5

# 查询并计算隐含增长率
acorn vi query 600900 -r "operating_cash_flow,market_cap" -y 5 -c implied_growth

# 列出所有可用字段
acorn vi list-fields

# 列出所有可用计算器
acorn vi list-calculators
```

### CLI 命令参数

| 参数 | 说明 |
|------|------|
| `-r, --fields` | 逗号分隔的字段名 |
| `-y, --years` | 查询年份数（默认 10） |
| `-c, --calculators` | 逗号分隔的计算器名 |
