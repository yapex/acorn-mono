# Value Investment Plugin

基于 Pluggy 的价值投资分析插件系统，为 Acorn 提供财务数据查询和计算能力。

## 架构概览

```
┌─────────────────────────────────────────────────────────────────┐
│                          vi_core                                 │
│                    (核心插件 + Plugin Manager)                   │
│                                                                 │
│  Commands: query, list_fields, list_calculators                 │
│  Entry Points: value_investment.{fields,providers,calculators}  │
└───────────────────────────┬─────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
        ▼                   ▼                   ▼
┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│    Fields     │   │   Providers   │   │  Calculators  │
├───────────────┤   ├───────────────┤   ├───────────────┤
│ vi_fields_ifrs│   │provider_tushare│   │vi_calculators │
│vi_fields_ext  │   │               │   │               │
│ (第三方扩展)   │   │ (第三方扩展)   │   │ (第三方扩展)   │
└───────────────┘   └───────────────┘   └───────────────┘
        │                   │                   │
        └───────────────────┼───────────────────┘
                            ▼
                   ┌───────────────┐
                   │vi_fields_ext  │
                   │(StandardFields)│
                   └───────────────┘
```

## 子项目

| 项目 | 职责 | 文档 |
|------|------|------|
| [vi_core](./vi_core/README.md) | 核心 Hook Spec + 查询引擎 | [README](./vi_core/README.md) |
| [vi_fields_extension](./vi_fields_extension/README.md) | 字段定义 + StandardFields 常量 | [README](./vi_fields_extension/README.md) |
| [vi_fields_ifrs](./vi_fields_ifrs/README.md) | IFRS 标准字段插件 | [README](./vi_fields_ifrs/README.md) |
| [vi_calculators](./vi_calculators/README.md) | 计算器加载器插件 | [README](./vi_calculators/README.md) |
| [provider_tushare](./provider_tushare/README.md) | Tushare 数据提供者 | [README](./provider_tushare/README.md) |
| [calculators](./calculators/README.md) | 内置计算器脚本 | [README](./calculators/README.md) |

## 快速开始

### 安装

```bash
# 使用 uv 安装
cd value-investment-plugin
uv sync
```

### 配置 Tushare Token

```bash
export TUSHARE_TOKEN="your_token_here"
```

### 使用示例

```python
from vi_core.plugin import plugin

# 设置 Plugin Manager
plugin.set_plugin_manager(pm)

# 查询财务数据
result = plugin._handle("query", {
    "symbol": "600519",
    "fields": "total_assets,roe,market_cap",
    "years": 5,
})

# 查询并计算隐含增长率
result = plugin._handle("query", {
    "symbol": "600519",
    "fields": "operating_cash_flow,market_cap",
    "calculators": "implied_growth",
})

# 列出所有可用字段
result = plugin._handle("list_fields", {})

# 列出所有计算器
result = plugin._handle("list_calculators", {})
```

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

```python
# my_provider/plugin.py
from vi_core.spec import FieldProviderSpec, vi_hookimpl
from vi_fields_extension import StandardFields

class MyProvider(FieldProviderSpec):
    FIELD_MAPPINGS = {
        "balance_sheet": {
            "api_field": StandardFields.new_field,
        }
    }

    @vi_hookimpl
    def vi_markets(self):
        return ["US"]

    @vi_hookimpl
    def vi_supported_fields(self):
        return ["new_field"]

    @vi_hookimpl
    def vi_fetch_financials(self, symbol, fields, end_year, years):
        # 获取数据...
        return {"new_field": {2023: 100}}

plugin = MyProvider()
```

```toml
# pyproject.toml
[project.entry-points."value_investment.providers"]
my_provider = "my_provider.plugin:plugin"
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

### 2. Hook 返回值

```python
# ✅ 数据获取成功
return {"field": {2023: 100}}

# ✅ 不支持该字段
return None

# ✅ 命令执行成功
return {"success": True, "data": {...}}

# ✅ 命令执行失败
return {"success": False, "error": "错误信息"}
```

### 3. 错误处理

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
pytest provider_tushare/tests/

# 运行集成测试（需要 TUSHARE_TOKEN）
pytest -m integration
```

## 目录结构

```
value-investment-plugin/
├── vi_core/                 # 核心插件
│   ├── src/vi_core/
│   │   ├── spec.py         # Hook Specs
│   │   └── plugin.py       # Plugin 实现
│   └── tests/
├── vi_fields_extension/     # 字段定义
│   └── src/vi_fields_extension/
│       ├── __init__.py     # register_fields API
│       ├── standard_fields.py  # FIELD_DEFINITIONS
│       └── plugin.py
├── vi_fields_ifrs/          # IFRS 字段
│   └── src/vi_fields_ifrs/
│       └── plugin.py
├── vi_calculators/          # 计算器加载器
│   └── src/vi_calculators/
│       └── __init__.py
├── provider_tushare/        # Tushare 提供者
│   ├── src/provider_tushare/
│   │   ├── provider.py     # TushareProvider
│   │   └── plugin.py
│   └── tests/
├── calculators/             # 计算器脚本
│   └── calc_implied_growth.py
├── vi_cli/                  # CLI 工具（可选）
├── tests/                   # 集成测试
└── pyproject.toml
```

## 相关文档

- [vi_fields_and_calculator_design.md](../../docs/vi-fields-and-calculator-design.md) - 设计讨论
- [Pluggy 文档](https://pluggy.readthedocs.io/)
