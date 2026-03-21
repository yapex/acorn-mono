# Value Investment Plugin 设计文档

> 自进化插件系统 - 财务分析能力

## 概述

基于 pluggy 插件框架，构建可扩展的财务数据分析系统。支持多数据源、多指标计算，统一字段标准。

## 设计目标

### 核心能力

1. **统一字段标准**：防腐层，所有数据转换为标准字段
2. **多数据源支持**：A 股、港股、美股
3. **可扩展指标**：Calculator 插件机制
4. **自进化能力**：支持第三方插件安装

### 使用场景

```
pi (AI Agent)
    │
    ├── Skill: financial-risk-screener
    │       │
    │       └── v-invest query 600519 -r "roe,gross_margin" -y 10
    │               │
    │               └── acorn RPC → query 命令
    │
    └── Skill: value-forge
            │
            └── 分析文档 → 生成新 Skill
```

## 架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                         acorn-agent                                 │
│                                                                      │
│   Acorn (pluggy)                                                     │
│   ┌─────────────────────────────────────────────────────────────┐   │
│   │  Command Plugins                                            │   │
│   │  - query: 查询数据                                          │   │
│   │  - register-calculator: 运行时注册 Calculator               │   │
│   └─────────────────────────────────────────────────────────────┘   │
│                              │                                       │
│                              ▼                                       │
│   ┌─────────────────────────────────────────────────────────────┐   │
│   │  vi_core (核心包)                                           │   │
│   │                                                              │   │
│   │   ┌─────────────────┐  ┌─────────────────┐                │   │
│   │   │  Field Registry  │  │ Calculator      │                │   │
│   │   │  (标准字段)      │  │ Registry        │                │   │
│   │   └─────────────────┘  └─────────────────┘                │   │
│   │                                                              │   │
│   │   ┌─────────────────────────────────────────────────┐      │   │
│   │   │  Query Engine                                    │      │   │
│   │   │  Provider 路由 → 数据获取 → Calculator 计算      │      │   │
│   │   └─────────────────────────────────────────────────┘      │   │
│   └─────────────────────────────────────────────────────────────┘   │
│                              │                                       │
│                              ▼                                       │
│   ┌─────────────────────────────────────────────────────────────┐   │
│   │  Provider Plugins (独立插件)                                 │   │
│   │   - provider_tushare    - provider_akshare                 │   │
│   │   - provider_yfinance                                          │   │
│   └─────────────────────────────────────────────────────────────┘   │
│                              │                                       │
│                              ▼                                       │
│   ┌─────────────────────────────────────────────────────────────┐   │
│   │  Calculator Plugins (独立插件)                               │   │
│   │   - calc_roe        - calc_gross_profit                    │   │
│   │   - calc_implied_growth                                     │   │
│   │   - ...                                                    │   │
│   └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ Unix Socket RPC
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                            vi_cli                                    │
│   v-invest query 600519 -r "roe" -y 5 --format markdown           │
└─────────────────────────────────────────────────────────────────────┘
```

## 插件规范

### pluggy 命名

| 层级 | 命名 | 说明 |
|------|------|------|
| project_name | `value_investment` | 固定，所有插件统一 |
| Provider entry_points | `value_investment.providers` | Provider 插件 |
| Calculator entry_points | `value_investment.calculators` | Calculator 插件 |

### Provider 插件

```toml
# provider_xxx/pyproject.toml
[project.entry-points."value_investment.providers"]
xxx = "provider_xxx:provider"
```

```python
# provider_xxx/src/provider_xxx/provider.py
from vi_core.spec import ProviderSpec, hookimpl

class MyProvider:
    @hookimpl
    def supported_markets(self):
        return ["A"]  # A股、HK港股、US美股
    
    @hookimpl
    def fetch_field(self, symbol, field, years):
        # 返回 {year: value}
        ...

provider = MyProvider()
```

### Calculator 插件

```toml
# calc_xxx/pyproject.toml
[project.entry-points."value_investment.calculators"]
xxx = "calc_xxx:calculator"
```

```python
# calc_xxx/src/calc_xxx/calc_xxx.py
# 文件名即 name：calc_xxx.py → name = "xxx"

required_fields = ["field_a", "field_b"]  # 必须

def calculate(results):  # 必须
    """
    results: {field: {year: value}}
    return: {year: value}
    """
    ...

# 以下全部可选
description = "描述"
version = "1.0"
```

### Provider 优先级

```python
class TushareProvider:
    @hookimpl(tryfirst=True)  # 优先尝试
    def fetch_field(self, symbol, field, years):
        ...

class AkShareProvider:
    @hookimpl(trylast=True)  # 失败时尝试
    def fetch_field(self, symbol, field, years):
        ...
```

## 字段体系

### 来源

直接复用 `value_investment/domain/fields.py`

### 分层

| 类型 | 说明 | 可扩展性 |
|------|------|----------|
| IFRSFields | 国际标准字段（冻结） | 不允许添加 |
| SourceFields | 数据源字段 | 通过 Provider 扩展 |
| IndicatorFields | 衍生指标 | 通过 Calculator 扩展 |

### Calculator 依赖

- 只允许依赖 Provider 返回的原始字段
- 不允许依赖其他 Calculator 输出

## CLI

### 命令风格

兼容现有 v-invest CLI：

```bash
v-invest query <symbol> -r <fields> [-y years] [--format format]

# 示例
v-invest query 600519 -r "roe,gross_margin,implied_growth" -y 10
v-invest query 00700 -r "roe" -m HK
```

### 输出格式

| 格式 | 说明 | 默认 |
|------|------|------|
| markdown | Markdown 表格 | ✓ |
| table | 终端表格 | |
| json | JSON | |

### 错误处理

部分失败不退出，标记 + 警告：

```bash
$ v-invest query 600519 -r "roe,unknown_field" -y 5
[WARNING] Field 'unknown_field' not supported, skipped
| 年份 | ROE     | unknown_field |
|------|---------|---------------|
| 2024 | 30.2%   | N/A          |
```

## 项目结构

```
value-investment-plugin/
│
├── pyproject.toml                 # uv workspace
│
├── vi_core/                       # 核心包
│   ├── pyproject.toml
│   └── src/vi_core/
│       ├── __init__.py
│       ├── field_registry.py      # 字段定义
│       ├── spec.py                # pluggy Hook 规范
│       ├── calculator_registry.py  # Calculator 注册
│       ├── calculator_loader.py   # 加载器
│       └── query_engine.py        # 查询引擎
│
├── provider_tushare/              # Provider 插件
│   ├── pyproject.toml
│   └── src/provider_tushare/
│
├── calculators/                   # Calculator 插件集合
│   ├── calc_implied_growth/
│   ├── calc_gross_profit/
│   └── ...
│
├── vi_cli/                        # CLI 插件
│   ├── pyproject.toml
│   └── src/vi_cli/
│
└── tests/
```

## Calculator 加载方式

| 方式 | 说明 |
|------|------|
| entry_points | `uv pip install calc-roe` 自动注册 |
| 文件扫描 | `~/.value_investment/calculators/` |
| 内存注册 | `CalculatorRegistry.register(...)` (RPC) |

## 后续扩展

- [ ] 运行时注册 Calculator (RPC 命令)
- [ ] 多 Provider 降级策略
- [ ] 缓存管理
- [ ] Calculator 依赖声明
- [ ] 第三方插件兼容性
- [ ] 错误处理 + 警告提示
