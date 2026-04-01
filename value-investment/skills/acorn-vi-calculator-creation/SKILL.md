---
name: acorn-vi-calculator-creation
description: Create financial calculators (估值指标) for the Acorn Value Investment system. Use when user wants to add a new calculator like ROE average, debt ratio, margin analysis, or any custom financial metric that doesn't exist yet.
---

# Acorn VI Calculator Creation

Create calculator scripts in `~/.value_investment/calculators/calc_{name}.py`.

## Step 1: Check Available Fields

**Before creating a calculator, you MUST check what standard fields are available.**

List all available fields:

```bash
acorn vi list --category fields
```

List fields for a specific market:

```bash
acorn vi list --category fields --market A
acorn vi list --category fields --market HK
acorn vi list --category fields --market US
```

Use standard field names in `REQUIRED_FIELDS`. Do NOT invent field names that don't exist.

## Quick Start

```python
# value-investment/calculators/calc_my_indicator.py
"""计算我的自定义指标"""

REQUIRED_FIELDS = ["field_a", "field_b"]
FORMAT_TYPE = "ratio"  # or "percentage", "market", "absolute"

def calculate(data):
    """Calculate my indicator

    Args:
        data: dict[str, pd.Series] - field data

    Returns:
        pd.Series - result with year as index
    """
    return data["field_a"] / data["field_b"].replace(0, float('nan'))
```

## Calculator File Location

- **Builtin**: `value-investment/calculators/calc_{name}.py` (packaged with wheel, do NOT modify)
- **CWD**: `<cwd>/calculators/calc_{name}.py` (user-defined calculators, recommended)

Loading order: builtin → cwd (cwd overrides builtin if same name).

**NOTE**: `acorn-agent` runs from the user's config directory, so `<cwd>/calculators/` is the standard location for new calculators.

## Required Structure

| Element | Required | Description |
|---------|----------|-------------|
| `REQUIRED_FIELDS` | ✅ | List of field names this calculator needs |
| `FORMAT_TYPE` | ✅ | Display format type (see below) |
| `calculate(data)` | ✅ | Function with exact signature |
| Docstring | ❌ | First line used as description |

## Display Format Type (FORMAT_TYPE)

Determines how the value appears in CLI output:

| FORMAT_TYPE | Example | Meaning |
|-------------|---------|---------|
| `"percentage"` | `38.43%` | Percentage (ROE, gross margin, etc.) |
| `"yoy"` | `15.00%` | Year-over-year growth rate |
| `"ratio"` | `4.45` | Ratio (current ratio, interest coverage, etc.) |
| `"market"` | `25.0` | Valuation metric (PE/PB, graham value) |
| `"absolute"` | `1741.44亿` | Monetary amount (default) |

```python
# Single-metric calculator
FORMAT_TYPE = "ratio"

# Multi-metric calculator (each metric has its own format)
FORMAT_TYPES = {
    "graham_value": "market",
    "margin_of_safety": "percentage",
}
```

## Naming Convention

| Part | Rule | Example |
|------|------|---------|
| File | `calc_{snake_name}.py` | `calc_debt_to_ebitda.py` |
| Calculator name | File without `calc_` prefix | `debt_to_ebitda` |
| Function | Must be `calculate` | `calculate(...)` |
| Variables | Full English, no abbreviations | `net_profit`, not `np` |

## Common Field Names

| Field | Chinese | Source |
|-------|---------|--------|
| `net_profit` | 净利润 | Income statement |
| `operating_cash_flow` | 经营现金流 | Cash flow statement |
| `total_assets` | 总资产 | Balance sheet |
| `total_equity` | 净资产 | Balance sheet |
| `interest_bearing_debt` | 有息负债 | Balance sheet |
| `ebitda` | 息税折旧摊销前利润 | Income statement |
| `market_cap` | 市值 | Market data |
| `basic_eps` | 每股收益 | Income statement |
| `book_value_per_share` | 每股净资产 | Balance sheet |
| `close` | 收盘价 | Market data |
| `roe` | 净资产收益率 | Calculated |
| `gross_profit` | 毛利 | Income statement |
| `total_revenue` | 营业收入 | Income statement |

## Common Calculation Patterns

```python
# Ratio (handle division by zero)
return data["a"] / data["b"].replace(0, float('nan'))

# Margin ((A - B) / A)
return (data["a"] - data["b"]) / data["a"]

# Year-over-year growth
return data["a"].pct_change()

# Average over period
return data["a"].mean()

# Sum
return data["a"].sum()
```

## Configuration (config parameter)

Currently the `config` parameter is reserved for future use. For now, hardcode defaults inside `calculate`:

```python
def calculate(data):
    wacc = 0.10
    g_terminal = 0.03
    # ... use in calculation
```

## Edge Cases

- **Division by zero**: Use `.replace(0, float('nan'))`
- **Missing data**: Return `pd.Series(dtype=float)` (empty Series)
- **Empty data**: Check `data["field"].dropna()` before calculating
- **No data**: Always return a Series (empty or with values), never None

## Verification

After creating, restart the CLI and check:

```bash
acorn vi list --category calculators
# Should show your new calculator with market codes
```

## Examples

### Example 1: Gross Profit Margin

```python
"""Calculate gross profit margin = (revenue - cost) / revenue"""

REQUIRED_FIELDS = ["gross_profit", "total_revenue"]
FORMAT_TYPE = "percentage"

def calculate(data):
    gp = data["gross_profit"]
    rev = data["total_revenue"]
    return ((rev - gp) / rev).replace(0, float('nan'))
```

### Example 2: Debt to Equity Ratio

```python
"""Calculate debt-to-equity ratio"""

REQUIRED_FIELDS = ["interest_bearing_debt", "total_equity"]
FORMAT_TYPE = "ratio"

def calculate(data):
    debt = data["interest_bearing_debt"]
    equity = data["total_equity"]
    return debt / equity.replace(0, float('nan'))
```

### Example 3: ROE Average (5-year)

```python
"""Calculate 5-year average ROE"""

REQUIRED_FIELDS = ["roe"]
FORMAT_TYPE = "percentage"

def calculate(data):
    roe = data["roe"].dropna()
    if len(roe) < 5:
        return pd.Series(dtype=float)
    return pd.Series(roe.mean())
```

### Example 4: Multi-metric Calculator

```python
"""Graham value with margin of safety"""

REQUIRED_FIELDS = ["basic_eps", "book_value_per_share", "close"]

# Each metric has its own format type
FORMAT_TYPES = {
    "graham_value": "market",
    "margin_of_safety": "percentage",
}

def calculate(data):
    eps = data["basic_eps"]
    bps = data["book_value_per_share"]
    close = data["close"]
    graham_value = (22.5 * eps * bps) ** 0.5
    margin_of_safety = (graham_value - close) / graham_value
    return {
        "values": pd.Series({
            "graham_value": graham_value,
            "margin_of_safety": margin_of_safety,
        }),
        "format_types": FORMAT_TYPES,
    }
```

## Extending SUPPORTED_MARKETS to New Markets

When extending a calculator to additional markets, ALL three conditions must be met:

### Condition 1: Target market has required raw fields

The calculator's `REQUIRED_FIELDS` must all exist in the target market's field list.

```bash
# 查看计算器的必需字段
acorn vi list --category calculators
# 找到目标计算器，查看 "必需字段" 行

# 查看目标市场的可用字段
acorn vi list --category fields --market HK
acorn vi list --category fields --market US

# 逐一比对：REQUIRED_FIELDS 中的每个字段是否出现在目标市场的字段列表中
```

Missing fields → **Cannot extend.**

### Condition 2: Target market does NOT already have the indicator as raw data

Check whether the indicator name already exists in the target market's field list.
If it does, the calculator would **overwrite** the more accurate API raw value.

```bash
# 计算器文件名去掉 calc_ 前缀即为指标名
# 例如 calc_debt_to_equity.py → 指标名为 debt_to_equity

# 在目标市场字段列表中搜索该指标名
acorn vi list --category fields --market A | grep debt_to_equity
acorn vi list --category fields --market HK | grep debt_to_equity
acorn vi list --category fields --market US | grep debt_to_equity

# 如果出现了 → 该市场已有原始指标数据，不能扩展
```

Already exists → **Cannot extend.** (would overwrite API raw value)

### Condition 3: Output field name matches standard field name

The calculator's file name without `calc_` prefix (the `calc_name`) must match the standard field name in `StandardFields`. The engine uses `calc_name` as the result key — downstream consumers depend on this name.

Example: `calc_debt_to_equity.py` → engine stores result as `results["debt_to_equity"]`

### Summary

**Has fields, no existing indicator, name matches → can extend.**

| Condition | Check | Not met → |
|-----------|-------|----------|
| Raw fields available | `REQUIRED_FIELDS` ⊆ market fields | Cannot extend |
| No raw indicator | Indicator not in `acorn vi list --category fields --market X` | Cannot extend (would overwrite) |
| Name matches standard | `calc_name` == `StandardFields.xxx` | Fix naming first |

Only add markets that pass ALL conditions to `SUPPORTED_MARKETS`.

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Calculator not found | Restart CLI to reload |
| Wrong results | Check REQUIRED_FIELDS matches actual field names |
| Import error | Don't use `import` inside calculate() |
| KeyError | Field name not in data - check spelling |
