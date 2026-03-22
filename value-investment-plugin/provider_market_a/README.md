# provider_tushare

Tushare 数据提供者插件，为 A 股市场提供财务数据。

## 职责

- 实现 `FieldProviderSpec` 的所有 Hook
- 提供 A 股市场的财务报表、指标、市场数据
- 将 Tushare API 字段映射到系统标准字段

## 架构

```
provider_tushare
├── src/provider_tushare/
│   ├── __init__.py
│   ├── provider.py     # TushareProvider 类
│   └── plugin.py       # Pluggy 插件包装
└── tests/
```

## 字段映射

Provider 通过 `FIELD_MAPPINGS` 定义 Tushare API 字段到系统标准字段的映射：

```python
from vi_fields_extension import StandardFields

FIELD_MAPPINGS = {
    "balance_sheet": {
        # Tushare API 字段 -> 系统标准字段
        "total_assets": StandardFields.total_assets,
        "total_liab": StandardFields.total_liabilities,
        "total_hldr_eqy_exc_min_int": StandardFields.total_equity,
        # ...
    },
    "income_statement": {
        "total_revenue": StandardFields.total_revenue,
        "n_income": StandardFields.net_profit,
        # ...
    },
    "cash_flow": {
        "n_cashflow_act": StandardFields.operating_cash_flow,
        # ...
    },
    "indicators": {
        "roe": StandardFields.roe,
        "roa": StandardFields.roa,
        "grossprofit_margin": StandardFields.gross_margin,
        # ...
    },
    "market": {
        "total_mv": StandardFields.market_cap,
        "pe_ttm": StandardFields.pe_ratio,
        "pb": StandardFields.pb_ratio,
        # ...
    },
}
```

### 使用 StandardFields 常量的好处

1. **避免硬编码**：字段名变更只需修改 `vi_fields_extension`
2. **IDE 支持**：`StandardFields.total_assets` 有自动补全
3. **类型安全**：引用不存在的字段会报错

## Hook 实现

```python
class TushareProvider:
    @vi_hookimpl
    def vi_markets(self) -> list[str]:
        return ["A"]  # 只支持 A 股

    @vi_hookimpl
    def vi_supported_fields(self) -> list[str]:
        # 从 FIELD_MAPPINGS 动态计算
        return list(self.get_supported_fields())

    @vi_hookimpl
    def vi_fetch_financials(self, symbol, fields, end_year, years) -> dict | None:
        # 获取资产负债表、利润表、现金流量表
        ...

    @vi_hookimpl
    def vi_fetch_indicators(self, symbol, fields, end_year, years) -> dict | None:
        # 获取财务指标
        ...

    @vi_hookimpl
    def vi_fetch_market(self, symbol, fields) -> dict:
        # 获取市场数据
        ...
```

## 数据获取流程

```
vi_core.query(symbol="600519", fields=["total_assets", "roe"])
        │
        ▼
┌───────────────────────────────────────────────────────────────┐
│ 1. 字段分类                                                    │
│    financial_fields = {"total_assets"}                        │
│    indicator_fields = {"roe"}                                 │
└───────────────────────────────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────────────────────────────┐
│ 2. 调用 vi_fetch_financials(fields=financial_fields)          │
│    TushareProvider:                                           │
│    - 判断字段属于 balance_sheet                                │
│    - 调用 Tushare API: balancesheet()                         │
│    - 过滤年报 (end_date ends with "1231")                      │
│    - 应用字段映射: "total_assets" -> "total_assets"            │
└───────────────────────────────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────────────────────────────┐
│ 3. 调用 vi_fetch_indicators(fields=indicator_fields)          │
│    TushareProvider:                                           │
│    - 调用 Tushare API: fina_indicator()                       │
│    - 应用字段映射: "roe" -> "roe"                              │
└───────────────────────────────────────────────────────────────┘
        │
        ▼
返回: {
    "total_assets": {2023: 1.2e12, 2022: 1.0e12},
    "roe": {2023: 0.15, 2022: 0.12}
}
```

## 配置

### 环境变量

```bash
export TUSHARE_TOKEN="your_token_here"
```

### 股票代码转换

Provider 自动将 6 位股票代码转换为 Tushare 的 ts_code 格式：

| 输入 | 转换后 |
|------|--------|
| `600519` | `600519.SH` |
| `000001` | `000001.SZ` |
| `300750` | `300750.SZ` |

## 开发规范

### 1. 添加新字段映射

```python
# 1. 先在 vi_fields_extension/standard_fields.py 中定义字段
FIELD_DEFINITIONS = {
    "new_field": {"description": "新字段", "category": "...", "source": "custom"},
}

# 2. 在 provider_tushare/provider.py 中添加映射
FIELD_MAPPINGS = {
    "balance_sheet": {
        "tushare_api_field": StandardFields.new_field,
    }
}
```

### 2. 返回值格式

```python
# 时间序列数据（财务报表、指标）
{field: {year: value}}

# 单点数据（市场数据）
{field: value}
```

### 3. 错误处理

- 字段不支持时返回 `None`（不是空字典）
- API 调用失败时返回 `None`
- 不要抛出异常

### 4. 年报过滤

```python
def _filter_annual_reports(self, df, date_col="end_date"):
    """只保留年报（end_date 以 1231 结尾）"""
    mask = df[date_col].astype(str).str.endswith("1231")
    return df[mask]
```

## 测试

```bash
# 运行测试
pytest provider_tushare/tests/

# 测试需要设置 TUSHARE_TOKEN
export TUSHARE_TOKEN="your_token"
pytest provider_tushare/tests/ -m integration
```

## 相关文档

- [vi_core 命令](../vi_core/README.md)
- [字段定义](../vi_fields_extension/README.md)
