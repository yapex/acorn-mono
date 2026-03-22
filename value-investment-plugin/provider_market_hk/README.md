# provider_market_hk

港股数据提供者，使用 AKShare API 获取数据。

## 职责

- 实现 `FieldProviderSpec` 的所有 Hook
- 提供港股市场的财务报表、指标、市场数据、历史交易数据
- 将 AKShare API 中文字段映射到系统标准字段

## 架构

```
provider_market_hk
├── src/provider_market_hk/
│   ├── __init__.py
│   ├── provider.py     # HKProvider 类
│   └── plugin.py      # Pluggy 插件包装
└── pyproject.toml
```

## 数据源

使用 [AKShare](https://akshare.akfamily.xyz/) API：

- `stock_financial_hk_report_em` - 财务报表（资产负债表、利润表、现金流量表）
- `stock_hk_financial_indicator_em` - 财务指标
- `stock_hk_company_profile_em` - 公司基本信息
- `stock_hk_daily` - 历史交易数据

## 字段映射

Provider 通过 `FIELD_MAPPINGS` 定义 AKShare API 中文字段到系统标准字段的映射：

```python
from vi_fields_extension import StandardFields

FIELD_MAPPINGS = {
    "balance_sheet": {
        # 中文字段 -> 标准字段
        "总资产": StandardFields.total_assets,
        "现金及等价物": StandardFields.cash_and_equivalents,
        # ...
    },
    "income_statement": {
        "收益": StandardFields.total_revenue,
        "毛利": StandardFields.gross_profit,
        # ...
    },
    # ...
}
```

## HK 特有字段

港股 Provider 额外支持以下字段（source="hk"）：

| 字段 | 说明 | 来源 |
|------|------|------|
| `hk_market_cap` | 港股市值(港元) | market |
| `hk_dividend_per_share` | 每股股息TTM(港元) | market |
| `hk_dividend_yield_ttm` | 股息率TTM(%) | market |
| `hk_dividend_payout_ratio` | 派息比率(%) | market |
| `hk_total_revenue_growth_qoq` | 营业总收入滚动环比增长(%) | ratio |
| `hk_net_profit_growth_qoq` | 净利润滚动环比增长(%) | ratio |
| `shareholders_equity` | 股东权益 | balance_sheet |
| `share_capital` | 股本 | balance_sheet |
| `gross_profit` | 毛利 | income_statement |
| `profit_before_tax` | 除税前溢利 | income_statement |

## 代码格式

港股代码使用 5 位数字格式：

| 输入 | 标准化后 |
|------|----------|
| `00700` | `00700` |
| `700` | `00700` |
| `腾讯` | `腾讯` |

## 使用示例

```python
from provider_market_hk import HKProvider

provider = HKProvider()

# 获取财务指标
df = provider.fetch_indicators(
    "00700",
    fields={"roe", "pe_ratio", "book_value_per_share", "hk_dividend_per_share"},
    end_year=2024,
    years=5,
)

# 获取财务报表
df = provider.fetch_financials(
    "00700",
    fields={"total_assets", "total_revenue", "parent_net_profit", "gross_profit"},
    end_year=2024,
    years=3,
)

# 获取市场数据
df = provider.fetch_market(
    "00700",
    fields={"hk_market_cap", "pe_ratio", "pb_ratio"},
)

# 获取历史交易数据（默认后复权）
df = provider.fetch_historical(
    "00700",
    start_date="2026-01-01",
    end_date="2026-03-20",
)
```

## 历史交易数据

```python
# 返回 DataFrame（默认后复权）
df = provider.fetch_historical("00700", start_date="2026-03-01", end_date="2026-03-20")
#            date   open   high    low  close      volume        amount
# 0    2026-03-01  520.0  528.0  515.0  525.5  18543210.0  9.72e+09
# ...

# 获取前复权历史数据
df = provider.fetch_historical("00700", adjust="qfq")

# 获取不复权历史数据
df = provider.fetch_historical("00700", adjust="")

# 通过 vi_fetch_historical hook
result = plugin.vi_fetch_historical(
    symbol="00700",
    start_date="2026-03-01",
    end_date="2026-03-20",
)
# 返回: {"date": [...], "open": [...], "high": [...], ...}
```

## 依赖

```toml
dependencies = [
    "akshare>=1.12.0",
    "vi-core>=0.1.0",
    "vi-fields-extension>=0.1.0",
]
```

## 开发规范

### 1. 添加新字段映射

```python
# 1. 先在 vi_fields_extension/standard_fields.py 中定义字段
FIELD_DEFINITIONS = {
    "new_field": {"description": "新字段", "category": "...", "source": "hk"},
}

# 2. 在 provider_market_hk/provider.py 中添加映射
FIELD_MAPPINGS = {
    "balance_sheet": {
        "AKShare字段名": StandardFields.new_field,
    }
}
```

### 2. 返回值格式

`fetch_*` 方法返回 `pd.DataFrame`，只包含映射后的标准字段：

```python
# 返回示例
df = provider.fetch_indicators("00700", {"roe", "pe_ratio"}, 2024, 5)
#    pe_ratio  hk_dividend_per_share  total_revenue  roe  book_value_per_share
# 0  18.618386                    4.5   751766000000  21.134746             126.54848
```

## 测试

```bash
# 运行测试（需要网络）
pytest tests/
```

## 相关文档

- [vi_core 命令](../vi_core/README.md)
- [字段定义](../vi_fields_extension/README.md)
