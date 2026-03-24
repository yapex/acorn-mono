---
name: calculator-creation
description: Create financial calculators for Value Investment system. Use when user requests a calculation that doesn't exist, or when vi_run_calculator returns extension_needed.
---

# Calculator Creation

## Quick Start

Create a file `calc_{field_name}.py` with:

```python
REQUIRED_FIELDS = ["field_a", "field_b"]

def calculate(data, config):
    """
    Calculate {field_name}

    Args:
        data: dict[str, pd.Series] - field data, key=field_name, value=Series(index=year)
        config: dict - user configuration

    Returns:
        pd.Series - calculation result with year as index
    """
    return data["field_a"] / data["field_b"]
```

## Workflows

### 1. Understand the requirement

- [ ] What is the field name? (must be snake_case)
- [ ] What is the formula?
- [ ] What fields are required?
- [ ] What is the unit? (ratio, percent, yuan)

### 2. Write the calculator

- [ ] Define REQUIRED_FIELDS list
- [ ] Implement calculate(data, config) function
- [ ] Handle edge cases (division by zero, missing data)

### 3. Register the calculator

```bash
acorn vi register-calculator \
  --name {field_name} \
  --code "$(cat calc_{field_name}.py)" \
  --required-fields "field_a,field_b" \
  --description "Description"
```

## Field Mapping

| Standard Field | Chinese | Category |
|---------------|---------|----------|
| interest_bearing_debt | 有息负债 | Balance |
| ebitda | 息税折旧摊销前利润 | Income |
| net_profit | 净利润 | Income |
| total_assets | 总资产 | Balance |
| total_equity | 净资产 | Balance |
| operating_cash_flow | 经营现金流 | Cash Flow |
| market_cap | 市值 | Market |

## Common Patterns

```python
# Ratio (A / B)
return data["a"] / data["b"].replace(0, float('nan'))

# Margin ((A - B) / A)
return (data["a"] - data["b"]) / data["a"]

# Growth ((current - previous) / previous)
return data["a"].pct_change()
```

## Constraints

- MUST define REQUIRED_FIELDS list
- Function name MUST be `calculate`
- Parameters MUST be `(data, config)`
- Return MUST be `pd.Series`
- FORBIDDEN: eval, exec, open, import (except pd), os, sys
