# provider_market_us

美股数据提供者，使用 AKShare API 获取数据。

## 职责

- 实现 `FieldProviderSpec` 的所有 Hook
- 提供美股市场的历史交易数据
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

- `stock_us_daily` - 美股历史交易数据（OHLCV）
- `stock_us_spot` - 美股实时行情
- `stock_individual_info_us` - 美股股票信息

## 字段映射

Provider 通过 `FIELD_MAPPINGS` 定义 AKShare API 字段到系统标准字段的映射：

```python
from vi_fields_extension import StandardFields

FIELD_MAPPINGS = {
    "daily": {
        "open": StandardFields.open,
        "high": StandardFields.high,
        "low": StandardFields.low,
        "close": StandardFields.close,
        "volume": StandardFields.volume,
    },
}
```

## 代码格式

美股代码支持标准格式（保持不变）：

| 输入 | 转换后 |
|------|--------|
| `AAPL` | `AAPL` |
| `GOOGL` | `GOOGL` |
| `aapl` | `AAPL` |

## 使用示例

```python
from provider_market_us import USProvider

provider = USProvider()

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

## 历史交易数据

```python
# 返回 DataFrame（默认前复权）
df = provider.fetch_historical("AAPL", start_date="2024-03-01", end_date="2024-03-20")
#         date    open    high     low   close     volume
# 0  2024-03-01  178.5  180.2  177.8  179.50  52000000.0
# ...

# 通过 vi_fetch_historical hook
result = plugin.vi_fetch_historical(
    symbol="AAPL",
    start_date="2024-03-01",
    end_date="2024-03-20",
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
    "new_field": {"description": "新字段", "category": "...", "source": "custom"},
}

# 2. 在 provider_market_us/provider.py 中添加映射
FIELD_MAPPINGS = {
    "daily": {
        "tushare_api_field": StandardFields.new_field,
    }
}
```

### 2. 返回值格式

`fetch_historical` 方法返回 `pd.DataFrame`：

```python
# 返回示例
df = provider.fetch_historical("AAPL", start_date="2024-01-01", end_date="2024-12-31")
#         date    open    high     low   close     volume
# 0  2024-01-02  185.0  186.5  184.2  185.80  45000000.0
# ...
```

## 相关文档

- [vi_core 命令](../vi_core/README.md)
- [字段定义](../vi_fields_extension/README.md)
