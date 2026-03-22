# provider_market_a

A 股数据提供者，使用 Tushare API 获取数据。

## 职责

- 实现 `FieldProviderSpec` 的所有 Hook
- 提供 A 股市场的财务报表、指标、市场数据、历史交易数据
- 将 Tushare API 字段映射到系统标准字段

## 架构

```
provider_market_a
├── src/provider_market_a/
│   ├── __init__.py
│   ├── provider.py     # TushareProvider 类
│   └── plugin.py       # Pluggy 插件包装
└── pyproject.toml
```

## 数据源

使用 [Tushare](https://tushare.pro/) API：

- `balancesheet` - 资产负债表
- `income` - 利润表
- `cashflow` - 现金流量表
- `fina_indicator` - 财务指标
- `daily_basic` - 每日市场数据
- `pro_bar` - 历史交易数据（OHLCV）

## 字段映射

Provider 通过 `FIELD_MAPPINGS` 定义 Tushare API 字段到系统标准字段的映射：

```python
from vi_fields_extension import StandardFields

FIELD_MAPPINGS = {
    "balance_sheet": {
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
    # ...
}
```

## 代码格式

A 股代码支持多种格式：

| 输入 | 转换后 |
|------|--------|
| `600519` | `600519.SH` |
| `000001` | `000001.SZ` |
| `300750` | `300750.SZ` |
| `600519.SH` | `600519.SH` (保持不变) |

## 配置

### 环境变量

```bash
export TUSHARE_TOKEN="your_token_here"
```

## 使用示例

```python
from provider_market_a import TushareProvider

provider = TushareProvider()

# 获取财务指标
df = provider.fetch_indicators(
    "600519",
    fields={"roe", "roa", "gross_margin", "net_profit_margin"},
    end_year=2024,
    years=5,
)

# 获取财务报表
df = provider.fetch_financials(
    "600519",
    fields={"total_assets", "total_revenue", "parent_net_profit"},
    end_year=2024,
    years=3,
)

# 获取市场数据
df = provider.fetch_market(
    "600519",
    fields={"market_cap", "pe_ratio", "pb_ratio"},
)

# 获取历史交易数据（默认后复权）
df = provider.fetch_historical(
    "600519",
    start_date="2024-01-01",
    end_date="2024-12-31",
    # adjust 默认为 "hfq" 后复权
)

# 获取前复权历史数据
df = provider.fetch_historical(
    "600519",
    start_date="2024-01-01",
    end_date="2024-12-31",
    adjust="qfq",
)

# 获取不复权历史数据
df = provider.fetch_historical(
    "600519",
    start_date="2024-01-01",
    end_date="2024-12-31",
    adjust="",
)
```

## A 股特定处理

### 1. 年报过滤

只保留年度财务报告（`end_date` 以 `1231` 结尾）：

```python
def _filter_annual_reports(self, df):
    mask = df["end_date"].astype(str).str.endswith("1231")
    return df[mask]
```

### 2. 数据去重

按 `update_flag` 排序，保留最新记录：

```python
def _deduplicate(self, df):
    # 按 update_flag 和日期排序
    df = df.sort_values([date_col, "update_flag"], ascending=[False, False])
    # 保留 update_flag 最新的记录
    return df.drop_duplicates(subset=[date_col], keep="last")
```

## 依赖

```toml
dependencies = [
    "tushare>=1.4.0",
    "vi-core>=0.1.0",
    "vi-fields-extension>=0.1.0",
]
```

## 开发规范

### 1. 添加新字段映射

```python
# 1. 先在 vi_fields_extension/standard_fields.py 中定义字段
FIELD_DEFINITIONS = {
    "new_field": {"description": "新字段", "category": "...", "source": "custom"},
}

# 2. 在 provider_market_a/provider.py 中添加映射
FIELD_MAPPINGS = {
    "balance_sheet": {
        "tushare_api_field": StandardFields.new_field,
    }
}
```

### 2. 返回值格式

`fetch_*` 方法返回 `pd.DataFrame`，只包含映射后的标准字段：

```python
# 返回示例
df = provider.fetch_indicators("600519", {"roe", "roa"}, 2024, 5)
#    end_date      roe       roa
# 0  20231231  0.2990  0.1523
# 1  20221231  0.2834  0.1421
```

## 测试

```bash
# 运行测试
pytest tests/

# 运行集成测试（需要 TUSHARE_TOKEN）
export TUSHARE_TOKEN="your_token"
pytest -m integration
```

## 相关文档

- [vi_core 命令](../vi_core/README.md)
- [字段定义](../vi_fields_extension/README.md)
