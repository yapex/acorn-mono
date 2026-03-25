# Calculator 脚本目录

存放内置计算器脚本，由 `vi_calculators` 插件自动发现和加载。

## 目录结构

```
calculators/
├── calc_implied_growth.py   # 隐含增长率计算器
├── calc_peg.py              # (待添加) PEG 计算器
└── calc_dcf.py              # (待添加) DCF 估值计算器
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

from typing import Any

# ✅ 必需：依赖的字段列表
REQUIRED_FIELDS = [
    "field_a",
    "field_b",
]

# ❌ 可选：默认配置
DEFAULT_CONFIG = {
    "param1": 0.1,
}

# ✅ 必需：计算函数
def calculate(
    results: dict[str, dict[int, Any]],
    config: dict[str, Any] | None = None,
) -> dict[int, Any]:
    """
    Args:
        results: 已获取的字段数据 {field: {year: value}}
        config: 用户传入的配置

    Returns:
        {year: value} 计算结果
    """
    pass
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

### laotang_valuation - 老唐估值法

基于唐朝《手把手教你读财报》的估值方法。

**计算逻辑**：
1. 计算最近5年净利润年化增长率 (CAGR)
2. 预估3年后净利润 = 当前净利润 × (1 + CAGR)³
3. 合理市值 = 3年后净利润 × 25倍PE
4. 理想买入价 = 合理市值 × 50%（安全边际已包含）
5. 卖出价 = 合理市值 × 200%

**必需字段**：
- `net_profit` - 净利润
- `basic_eps` - 每股收益
- `close` - 当前股价

**配置参数**：
| 参数 | 默认值 | 说明 |
|------|--------|------|
| `pe_ratio` | 25 | 合理PE倍数 |
| `buy_ratio` | 0.50 | 买入折扣（安全边际） |
| `sell_ratio` | 2.00 | 卖出倍数 |
| `min_years` | 5 | 计算CAGR所需最小年数 |

**使用示例**：
```bash
# CLI
acorn vi query 600519 --items net_profit,basic_eps,close,laotang_valuation --years 5
```

```python
# Python
result = vi_handle("query", {
    "symbol": "600519",
    "items": "net_profit,basic_eps,close,laotang_valuation",
    "years": 5,
})
# 返回:
# {
#   "buy_price": 1335.5,      # 理想买入价（每股）
#   "sell_price": 5342.02,    # 卖出价（每股）
#   "current_price": 1407.33, # 当前股价
#   "gap": -5.1,              # 与买入价差距 (%)
#   ...
# }
```

**gap 解读**：
- 正值：当前股价低于买入价，可以考虑买入
- 负值：当前股价高于买入价，需要等待

## 添加新计算器

### 1. 创建脚本文件

```python
# calculators/calc_roe_avg.py
"""计算 ROE 平均值"""

from typing import Any

REQUIRED_FIELDS = ["roe"]

def calculate(results, config=None):
    roe_data = results.get("roe", {})
    if not roe_data:
        return {}

    avg = sum(roe_data.values()) / len(roe_data)
    # 返回最新年份的结果
    latest_year = max(roe_data.keys())
    return {latest_year: avg}
```

### 2. 重启应用

vi_calculators 会在启动时自动发现新脚本。

### 3. 验证

```python
result = vi_handle("list_calculators", {})
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
