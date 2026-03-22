# VI Fields and Calculator Design Discussion

Date: 2024-03-22

## 1. Field Architecture

### 1.1 Problem: Provider Bypasses System Field Definitions

The Tushare Provider was defining its own `SUPPORTED_FIELDS` and `FIELD_MAPPINGS`, bypassing the system's field definitions.

**Solution**: 
- Provider's `vi_supported_fields` is dynamically computed from `FIELD_MAPPINGS`
- `FIELD_MAPPINGS` uses `StandardFields` constants instead of hardcoded strings

### 1.2 StandardFields Constants

```python
# standard_fields.py
class StandardFields:
    total_assets = _StandardField("total_assets")
    total_liabilities = _StandardField("total_liabilities")
    # ...
```

Provider mapping uses constants:
```python
FIELD_MAPPINGS = {
    "balance_sheet": {
        "total_assets": StandardFields.total_assets,
    }
}
```

**Benefits**: When field names change, only update `StandardFields`.

### 1.3 vi_fields Hook Returns Dict (Not Set)

Changed from:
```python
{"source": "ifrs", "fields": set()}
```

To:
```python
{"source": "ifrs", "fields": {"total_assets": {"description": "资产总计", "category": "balance_sheet"}}}
```

### 1.4 Single Source of Truth

```
standard_fields.py
├── IFRS_FIELDS (38)
├── CUSTOM_FIELDS (47)  
├── ALL_BUILTIN_FIELDS = IFRS + CUSTOM (85)
├── FIELD_DEFINITIONS (with descriptions)
└── StandardFields (85 constants for Provider mapping)
```

## 2. pluggy Hook Spec vs Hook Implementation

### 2.1 Basic Concepts

```python
# Hook Spec - defines the "slot"
class FieldRegistrySpec:
    @vi_hookspec  # marks this as a hook spec
    def vi_fields(self):
        return {"source": "", "fields": {}}

# Hook Implementation - provides the "plug"
class IfrsPlugin(FieldRegistrySpec):
    @vi_hookimpl  # marks this as an implementation
    def vi_fields(self):
        return {"source": "ifrs", "fields": {...}}
```

### 2.2 How pluggy Works

```python
pm = pluggy.PluginManager("value_investment")
pm.add_hookspecs(FieldRegistrySpec)  # register the slot

pm.register(IfrsPlugin())  # plug in

results = pm.hook.vi_fields()  # pluggy auto-discovers and calls all implementations
```

### 2.3 Multiple Hooks in One Spec

```python
class ValueInvestmentSpecs:
    @vi_hookspec
    def vi_fields(self): ...  # Hook point 1
    
    @vi_hookspec
    def vi_supported_fields(self): ...  # Hook point 2
    
    @vi_hookspec
    def vi_fetch_financials(self): ...  # Hook point 3
```

**Method name is the matching key**. pluggy auto-matches implementations by method name.

### 2.4 When to Use Multiple Specs?

| Approach | Use Case |
|---------|----------|
| Multiple Specs | Large system, clear responsibility boundaries |
| Single Spec | Small/simple system |

**Conclusion**: Specs should align with responsibility boundaries, not artificially created complexity.

## 3. FieldsExtensionSpec - Removed

Initially created `FieldsExtensionSpec` as an extension point for third-party field providers.

**Realized it's unnecessary** because:
- `FieldRegistrySpec.vi_fields()` is already an extension point
- Third-party can either:
  1. Use `register_fields()` function
  2. Directly implement `FieldRegistrySpec`

```python
# Option 1: register_fields
from vi_fields_extension import register_fields
register_fields(source="wind", fields={"sector": "所属行业"})

# Option 2: Direct implementation
from vi_core.spec import FieldRegistrySpec, vi_hookimpl

class WindFieldsPlugin(FieldRegistrySpec):
    @vi_hookimpl
    def vi_fields(self):
        return {"source": "wind", "fields": {...}}
```

## 4. Calculator Auto-Discovery

### 4.1 Current Design

```
CalculatorLoaderPlugin (pluggy plugin)
├── vi_list_calculators()
└── vi_run_calculator()
        │
        │ discovers
        ▼
calc_implied_growth.py (plain Python module)
├── REQUIRED_FIELDS = [...]
└── calculate(results, config) -> dict
```

**Issue**: Calculator scripts are plain modules, not pluggy plugins.

### 4.2 Decorator Approach for Auto-Discovery

Proposed solution using decorators:

```python
# vi_core/calculators.py
from vi_core.spec import CalculatorSpec, vi_hookimpl

def calculator(name: str, required_fields: list[str]):
    """Decorator: turns a function into a pluggy plugin"""
    def decorator(fn):
        class CalcPlugin(CalculatorSpec):
            @vi_hookimpl
            def vi_calculate(self, data, config):
                return fn(data, config)
            
            @vi_hookimpl
            def vi_list_calculators(self):
                return [{"name": name, "required_fields": required_fields}]
        
        plugin = CalcPlugin()
        _CALCULATOR_PLUGINS[name] = plugin
        return plugin
    return decorator

# Global registry
_CALCULATOR_PLUGINS = {}

def get_calculator_plugins():
    return _CALCULATOR_PLUGINS
```

### 4.3 Usage

```python
# calc_implied_growth.py
from vi_core.calculators import calculator

@calculator("implied_growth", required_fields=["operating_cash_flow", "market_cap"])
def calculate(data, config):
    # ... business logic
    return implied_growth_rate(data, config)
```

**Benefits**:
- Calculator developers only focus on business logic
- Auto-registration with pluggy
- No need to inherit from Spec or add `@vi_hookimpl` manually

### 4.4 Alternative: Base Class

```python
class CalculatorBase(CalculatorSpec):
    REQUIRED_FIELDS: list[str] = []
    
    def calculate(self, data, config):
        raise NotImplementedError
    
    @vi_hookimpl
    def vi_calculate(self, data, config):
        return self.calculate(data, config)

# Usage
class ImpliedGrowthCalculator(CalculatorBase):
    REQUIRED_FIELDS = ["operating_cash_flow", "market_cap"]
    
    def calculate(self, data, config):
        # ... logic
        return result

plugin = ImpliedGrowthCalculator()
```

### 4.5 Comparison

| Approach | Complexity | Flexibility |
|----------|------------|-------------|
| Decorator | Low | Medium |
| Base Class | Low | High |
| Current Manual | High | High |

**Decision**: Decorator approach is simplest for calculator developers.

## 5. Final Architecture

```
vi_fields Hook Chain
────────────────────
FieldRegistrySpec.vi_fields()
        ▲
        │
   ┌────┴─────────────────────┐
   │                          │
IfrsPlugin.vi_fields()  ViFieldsExtensionPlugin.vi_fields()
(returns IFRS fields)   (aggregates all extension fields)
```

```
Calculator Discovery (Future)
─────────────────────────────
@calculator decorator
        │
        ▼
CalculatorLoaderPlugin (aggregates via _CALCULATOR_PLUGINS)
```

## 6. Open Questions

1. **Should calculators use the decorator approach?** Need implementation.
2. **How to aggregate third-party calculators?** Same mechanism as fields - via pluggy.
