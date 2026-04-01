# Calculator 脚本目录

存放内置计算器脚本，由 `vi_calculators` 插件自动发现和加载。

## 目录结构

```
calculators/
├── calc_asset_turnover.py      # 资产周转率
├── calc_book_value_per_share.py # 每股净资产
├── calc_cagr.py                 # 年复合增长率
├── calc_currentdebt_to_debt.py  # 流动负债/总负债
├── calc_debt_to_ebitda.py      # 债务/EBITDA
├── calc_debt_to_equity.py      # 产权比率
├── calc_free_cash_flow.py       # 自由现金流
├── calc_graham_value.py         # 格雷厄姆估值
├── calc_gross_profit.py        # 毛利
├── calc_implied_growth.py       # 隐含增长率
├── calc_interest_coverage.py   # 利息保障倍数
├── calc_inventory_turnover.py  # 存货周转率
├── calc_net_debt_ratio.py      # 净债务率
├── calc_non_current_assets.py  # 非流动资产
├── calc_non_current_liabilities.py # 非流动负债
├── calc_npcf_ratio.py          # NPCF比率
├── calc_operating_profit_margin.py # 营业利润率
├── calc_pb_ratio.py            # 市净率
├── calc_pe_ratio.py            # 市盈率
├── calc_quick_ratio.py         # 速动比率
├── calc_receivable_turnover.py # 应收账款周转率
├── calc_roic.py                # 投入资本回报率
└── calc_volatility.py          # 盈利波动率
```

## 脚本规范

### 文件命名

- 必须以 `calc_` 开头
- 使用下划线命名法：`calc_implied_growth.py`
- 计算器名称 = 文件名去掉 `calc_` 前缀

### 必需元素

```python
# calc_xxx.py
"""计算器描述（第一行作为简短描述）"""

# ✅ 必需：依赖的字段列表
REQUIRED_FIELDS = [
    "field_a",
    "field_b",
]

# ✅ 必需：显示格式类型（见下方格式类型说明）
FORMAT_TYPE = "ratio"  # 或 FORMAT_TYPES = {"metric_a": "ratio", "metric_b": "percentage"}

# ❌ 可选：默认配置
DEFAULT_CONFIG = {
    "param1": 0.1,
}

# ✅ 必需：计算函数
def calculate(data):
    """
    Args:
        data: dict[str, pd.Series] - 字段数据，{field: Series(index=年份)}

    Returns:
        pd.Series - 单指标结果，Series(index=年份)
        或 dict: {"values": pd.Series, "format_types": {"metric": "ratio", ...}}  多指标结果
    """
    return data["field_a"] / data["field_b"].replace(0, float('nan'))
```

### 显示格式类型（FORMAT_TYPE）

Calculator 必须声明自己的显示格式，影响 CLI 输出时的格式：

| FORMAT_TYPE | 示例 | 含义 |
|---|---|---|
| `"percentage"` | `38.43%` | 百分比，显示时加 % 后缀 |
| `"yoy"` | `15.00%` | 同比增长率，显示时加 % 后缀 |
| `"ratio"` | `4.45` | 比率，显示时不加 % |
| `"market"` | `25.0` | 估值指标（PE/PB 等） |
| `"absolute"` | `1741.44亿` | 金额，按数量级加 亿/万 后缀（默认） |

```python
# 单指标 calculator
FORMAT_TYPE = "ratio"

# 多指标 calculator（每个 metric 独立声明格式）
FORMAT_TYPES = {
    "graham_value": "market",
    "margin_of_safety": "percentage",
}
```

### 返回值规范

```python
# ✅ 单指标：返回 pd.Series
return data["field_a"] / data["field_b"].replace(0, float('nan'))

# ✅ 多指标：返回 dict（含 format_types）
return {
    "values": pd.Series({
        "graham_value": graham_value,
        "margin_of_safety": margin_of_safety,
    }),
    "format_types": {
        "graham_value": "market",
        "margin_of_safety": "percentage",
    },
}

# ✅ 无数据：返回空 Series
return pd.Series(dtype=float)

# ❌ 不要返回 None
# ❌ 不要抛出异常（会显示为错误）
```

### 返回值规范

```python
# ✅ 正常返回
{2023: 0.15, 2022: 0.12}

# ✅ 无数据
{}

# ❌ 不要返回 None
# ❌ 不要抛出异常
```

## 内置计算器

### implied_growth - 隐含增长率

基于 DCF 模型，用市值反推市场隐含的年增长率。

**必需字段**：
- `operating_cash_flow` - 经营活动现金流
- `market_cap` - 总市值

**配置参数**：
| 参数 | 默认值 | 说明 |
|------|--------|------|
| `wacc` | 0.10 | 加权平均资本成本 |
| `g_terminal` | 0.03 | 永续增长率 |
| `n_years` | 10 | 预测年数 |

**使用示例**：
```python
result = vi_handle("query", {
    "symbol": "600519",
    "fields": "operating_cash_flow,market_cap",
    "calculators": "implied_growth",
    "calculator_config": {
        "implied_growth": {"wacc": 0.08}
    }
})
# result["data"]["implied_growth"] = {2023: 0.12}
```

## 添加新计算器

### 1. 创建脚本文件

```python
# calculators/calc_roe_avg.py
"""计算 ROE 平均值"""

import pandas as pd

REQUIRED_FIELDS = ["roe"]
FORMAT_TYPE = "percentage"

def calculate(data):
    roe = data["roe"].dropna()
    if roe.empty:
        return pd.Series(dtype=float)
    # 返回最新年份的平均值
    return pd.Series(roe.mean())
```

### 2. 重启应用

vi_calculators 会在启动时自动发现新脚本。

### 3. 验证

```bash
acorn vi list --category calculators
# 应该看到 {"name": "roe_avg", "required_fields": ["roe"], ...}
```

## 用户自定义计算器

用户可以在 `~/.value_investment/calculators/` 目录下创建自己的计算器：

```bash
mkdir -p ~/.value_investment/calculators
```

```python
# ~/.value_investment/calculators/calc_my_indicator.py
"""我的自定义指标"""

REQUIRED_FIELDS = ["total_assets", "total_revenue"]

def calculate(results, config=None):
    # 自定义计算逻辑
    pass
```

用户计算器会被自动发现，命名空间为 `user`。

## 调试技巧

### 1. 查看已加载的计算器

```python
result = vi_handle("list_calculators", {})
for calc in result["data"]["calculators"]:
    print(f"{calc['name']}: {calc['required_fields']}")
```

### 2. 测试单个计算器

```python
# 直接调用（不通过 vi_core）
from vi_calculators import get_all_calculators

calcs = get_all_calculators()
for c in calcs:
    if c["name"] == "implied_growth":
        result = c["module"].calculate(
            {"operating_cash_flow": {2023: 100e8}, "market_cap": {2023: 5000e8}},
            {}
        )
        print(result)
```

### 3. 检查字段依赖

```python
# 查看计算器需要哪些字段
calc_name = "implied_growth"
result = vi_handle("list_calculators", {})
for c in result["data"]["calculators"]:
    if c["name"] == calc_name:
        print(f"Required: {c['required_fields']}")
```

## 相关文档

- [vi_calculators 插件](../vi_calculators/README.md)
- [vi_core 命令](../vi_core/README.md)
