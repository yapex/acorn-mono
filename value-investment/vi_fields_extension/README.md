# vi_fields_extension

字段扩展注册中心，提供系统标准字段的单一数据源。

## 职责

- 定义 `FIELD_DEFINITIONS`（所有字段的单一真相来源）
- 提供 `StandardFields` 常量类
- 提供 `register_fields()` 函数式 API
- 聚合所有扩展字段

## 字段定义结构

```python
FIELD_DEFINITIONS = {
    "total_assets": {
        "description": "资产总计",
        "category": "balance_sheet",  # balance_sheet, income_statement, cash_flow, ratio, market, trading
        "source": "ifrs",             # ifrs, custom
    },
    "roe": {
        "description": "净资产收益率 (ROE)",
        "category": "ratio",
        "source": "ifrs",
    },
    # ...
}
```

## 使用方式

### 1. 在 Provider 中引用字段常量

```python
from vi_fields_extension import StandardFields

class MyProvider:
    FIELD_MAPPINGS = {
        "balance_sheet": {
            # API 原始字段名 -> 系统标准字段名
            "total_assets": StandardFields.total_assets,
            "total_liab": StandardFields.total_liabilities,
        }
    }
```

**好处**：字段名变更时只需更新 `FIELD_DEFINITIONS`。

### 2. 查询字段信息

```python
from vi_fields_extension import FIELD_DEFINITIONS, IFRS_FIELDS, CUSTOM_FIELDS

# 获取字段描述
desc = FIELD_DEFINITIONS["total_assets"]["description"]

# 获取所有 IFRS 字段
ifrs_fields = IFRS_FIELDS  # set[str]

# 获取字段来源
source = FIELD_TO_SOURCE["total_assets"]  # "ifrs"
```

### 3. 注册扩展字段（函数式 API）

```python
from vi_fields_extension import register_fields

register_fields(
    source="wind",
    fields={
        "sector": "所属行业",
        "dividend_yield": "股息率",
    }
)
```

**注意**：这种方式需要先 import 你的模块才能注册。

### 4. 注册扩展字段（Pluggy 插件，推荐）

```python
# my_plugin/plugin.py
from vi_core.spec import FieldRegistrySpec, vi_hookimpl

class WindFieldsPlugin(FieldRegistrySpec):
    @vi_hookimpl
    def vi_fields(self):
        return {
            "source": "wind",
            "fields": {
                "sector": {"description": "所属行业"},
                "dividend_yield": {"description": "股息率"},
            },
            "description": "Wind 金融终端字段",
        }

plugin = WindFieldsPlugin()
```

```toml
# pyproject.toml
[project.entry-points."value_investment.fields"]
wind = "my_plugin.plugin:plugin"
```

**好处**：vi_core 自动发现，无需显式 import。

## 字段分类

| Category | 说明 | 示例 |
|----------|------|------|
| `balance_sheet` | 资产负债表 | total_assets, total_equity |
| `income_statement` | 利润表 | total_revenue, net_profit |
| `cash_flow` | 现金流量表 | operating_cash_flow |
| `ratio` | 财务比率 | roe, gross_margin |
| `market` | 市场数据 | market_cap, pe_ratio |
| `trading` | 交易数据 | close, volume |
| `calculated` | 计算字段 | ebit, net_debt |

## 字段来源

| Source | 说明 |
|--------|------|
| `ifrs` | IFRS 国际财务报告准则标准字段 |
| `custom` | 系统内置扩展字段 |
| 第三方定义 | 通过 `register_fields` 或 Pluggy 插件注册 |

## 开发规范

1. **新增字段**：在 `standard_fields.py` 的 `FIELD_DEFINITIONS` 中添加
2. **Provider 映射**：使用 `StandardFields.xxx` 常量，不要硬编码字符串
3. **第三方字段**：优先使用 Pluggy 插件方式注册

## 导出清单

```python
from vi_fields_extension import (
    # 字段定义
    FIELD_DEFINITIONS,      # dict[str, dict]
    IFRS_FIELDS,            # set[str]
    CUSTOM_FIELDS,          # set[str]
    ALL_BUILTIN_FIELDS,     # set[str]
    FIELD_TO_SOURCE,        # dict[str, str]

    # 常量类
    StandardFields,         # 类属性访问，如 StandardFields.total_assets

    # 函数式 API
    register_fields,        # 注册扩展字段
    get_extension_fields,   # 获取已注册的扩展字段
    clear,                  # 清除注册（测试用）

    # Pluggy 插件
    plugin,                 # ViFieldsExtensionPlugin 实例
)
```
