# provider_market_us

美股数据提供者，使用 AKShare API 获取数据。

## 职责

- 实现 `FieldProviderSpec` 的所有 Hook
- 提供美股市场的财务报表、财务指标、历史交易数据
- 将 AKShare API 字段映射到系统标准字段

## 架构

```
provider_market_us
├── src/provider_market_us/
│   ├── __init__.py
│   ├── provider.py     # USProvider 类
│   └── plugin.py       # Pluggy 插件包装
└── pyproject.toml
```

## 数据源

使用 [AKShare](https://akshare.akfamily.xyz/) API：

- `stock_financial_us_report_em` - 美股三大财务报表（资产负债表、利润表、现金流量表）
- `stock_financial_us_analysis_indicator_em` - 美股财务指标
- `stock_us_daily` - 美股历史交易数据（OHLCV）
- `stock_us_spot` - 美股实时行情
- `stock_individual_info_us` - 美股股票信息

## 代码格式

美股代码支持标准格式（保持不变）：

| 输入 | 转换后 |
|------|--------|
| `AAPL` | `AAPL` |
| `GOOGL` | `GOOGL` |
| `aapl` | `AAPL` |

## 使用示例

### 获取财务报表

```python
from provider_market_us import USProvider

provider = USProvider()

# 获取财务报表（资产负债表、利润表、现金流量表合并）
df = provider.fetch_financials(
    "AAPL",
    fields={"total_assets", "total_revenue", "net_profit", "parent_net_profit"},
    end_year=2024,
    years=5,
)
```

### 获取财务指标

```python
# 获取财务指标（ROE, ROA, 毛利率, 净利率, EPS 等）
df = provider.fetch_indicators(
    "AAPL",
    fields={"roe", "roa", "gross_margin", "net_profit_margin", "basic_eps"},
    end_year=2024,
    years=5,
)
```

### 获取历史交易数据

```python
# 获取历史交易数据（默认前复权）
df = provider.fetch_historical(
    "AAPL",
    start_date="2024-01-01",
    end_date="2024-12-31",
)

# 获取前复权历史数据
df = provider.fetch_historical(
    "AAPL",
    start_date="2024-01-01",
    end_date="2024-12-31",
    adjust="qfq",
)

# 获取不复权历史数据
df = provider.fetch_historical(
    "AAPL",
    start_date="2024-01-01",
    end_date="2024-12-31",
    adjust="",
)
```

## 字段映射

Provider 通过 `FIELD_MAPPINGS` 定义 AKShare API 字段到系统标准字段的映射：

```python
FIELD_MAPPINGS = {
    "balance_sheet": {
        "现金及现金等价物": StandardFields.cash_and_equivalents,
        "应收账款": StandardFields.accounts_receivable,
        "存货": StandardFields.inventory,
        "总资产": StandardFields.total_assets,
        "总负债": StandardFields.total_liabilities,
        "总权益": StandardFields.total_equity,
        # ...
    },
    "income_statement": {
        "营业收入": StandardFields.total_revenue,
        "净利润": StandardFields.net_profit,
        "毛利": StandardFields.gross_profit,
        "基本每股收益-普通股": StandardFields.basic_eps,
        # ...
    },
    "cash_flow": {
        "经营活动产生的现金流量净额": StandardFields.operating_cash_flow,
        "购买固定资产": StandardFields.capital_expenditure,
        # ...
    },
    "indicators": {
        "ROE_AVG": StandardFields.roe,
        "ROA": StandardFields.roa,
        "GROSS_PROFIT_RATIO": StandardFields.gross_margin,
        "NET_PROFIT_RATIO": StandardFields.net_profit_margin,
        "BASIC_EPS": StandardFields.basic_eps,
        # ...
    },
    "daily": {
        "open": StandardFields.open,
        "high": StandardFields.high,
        "low": StandardFields.low,
        "close": StandardFields.close,
        "volume": StandardFields.volume,
    },
}
```

## 返回值格式

### 财务报表

```python
df = provider.fetch_financials("AAPL", {"total_assets", "total_revenue"}, 2024, 5)
#    REPORT_DATE    total_assets   total_revenue  net_profit
# 0  2025-09-27    3.592410e+11  4.161610e+11  1.120100e+11
# 1  2024-09-28    3.649800e+11  3.910350e+11  9.373600e+10
# ...
```

### 财务指标

```python
df = provider.fetch_indicators("AAPL", {"roe", "roa", "basic_eps"}, 2024, 5)
#    REPORT_DATE    roe        roa    basic_eps
# 0  2025-09-27    171.42     30.93   7.49
# 1  2024-09-28    157.41     26.13   6.11
# ...
```

### 历史交易数据

```python
df = provider.fetch_historical("AAPL", start_date="2024-03-01", end_date="2024-03-10")
#         date    open    high     low   close     volume
# 0  2024-03-01  178.5  180.2  177.8  179.50  52000000.0
# ...
```

## 通过 Hook 调用

```python
from provider_market_us import plugin

# 获取历史交易数据
result = plugin.vi_fetch_historical(
    symbol="AAPL",
    start_date="2024-03-01",
    end_date="2024-03-10",
)
# 返回: {"date": [...], "open": [...], "high": [...], "low": [...], "close": [...], "volume": [...]}
```

## 依赖

```toml
dependencies = [
    "akshare>=1.12.0",
    "vi-core>=0.1.0",
    "vi-fields-extension>=0.1.0",
]
```

## 相关文档

- [vi_core 命令](../vi_core/README.md)
- [字段定义](../vi_fields_extension/README.md)
