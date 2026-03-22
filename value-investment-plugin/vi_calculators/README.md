# vi_calculators

计算器加载器插件，自动发现并执行 Calculator 脚本。

## 职责

- 从文件系统发现 Calculator 脚本
- 提供 `vi_list_calculators` 和 `vi_run_calculator` Hook 实现
- 支持动态注册 Calculator
- 管理命名空间（builtin / user / dynamic）

## 架构

```
vi_calculators
├── __init__.py        # CalculatorLoaderPlugin
└── (依赖 vi_core)

calculators/           # Calculator 脚本目录
├── calc_implied_growth.py
├── calc_peg.py
└── ...
```

## Calculator 脚本规范

### 基本结构

```python
# calculators/calc_xxx.py
"""Calculator 描述（第一行会作为简短描述）"""

from typing import Any

# 必需字段列表
REQUIRED_FIELDS = [
    "operating_cash_flow",
    "market_cap",
]

# 默认配置（可选）
DEFAULT_CONFIG = {
    "wacc": 0.10,
    "g_terminal": 0.03,
    "n_years": 10,
}


def calculate(
    results: dict[str, dict[int, Any]],
    config: dict[str, Any] | None = None,
) -> dict[int, Any]:
    """计算逻辑

    Args:
        results: {field: {year: value}} 已获取的字段数据
        config: 用户传入的配置

    Returns:
        {year: value} 计算结果
    """
    cfg = {**DEFAULT_CONFIG, **(config or {})}
    # ... 计算逻辑
    return {2023: 0.15, 2022: 0.12}
```

### 命名规范

- 文件名：`calc_<name>.py`（必须以 `calc_` 开头）
- 计算器名称：文件名去掉 `calc_` 前缀，如 `calc_implied_growth.py` → `implied_growth`

### 必需元素

| 元素 | 必须 | 说明 |
|------|------|------|
| `REQUIRED_FIELDS` | ✅ | 依赖的字段列表 |
| `calculate(results, config)` | ✅ | 计算函数 |
| `DEFAULT_CONFIG` | ❌ | 默认配置 |
| `__doc__` | ❌ | 描述文档 |

### 返回值

```python
# 正常返回
{2023: 0.15, 2022: 0.12}

# 无数据返回空字典
{}
```

## 命名空间

| Namespace | 路径 | 信任级别 |
|-----------|------|----------|
| `builtin` | `value-investment-plugin/calculators/` | 可信 |
| `user` | `~/.value_investment/calculators/` | 用户自定义 |
| `dynamic` | 运行时注册 | 未验证 |

## Hook 实现

```python
class CalculatorLoaderPlugin(CalculatorSpec):
    @vi_hookimpl
    def vi_list_calculators(self) -> list[dict]:
        """返回所有已加载的计算器"""

    @vi_hookimpl
    def vi_run_calculator(self, name, data, config) -> dict | None:
        """执行计算器"""

    @vi_hookimpl
    def vi_register_calculator(self, name, code, required_fields, namespace, description) -> dict:
        """动态注册计算器"""
```

## 动态注册

```python
# 通过命令动态注册
result = vi_handle("register_calculator", {
    "name": "my_calc",
    "code": """
def calculate(results, config):
    return {2023: 1.0}
""",
    "required_fields": ["total_assets"],
    "description": "我的计算器",
    "namespace": "dynamic",
})
```

## 使用示例

### 1. 查询时调用计算器

```python
result = vi_handle("query", {
    "symbol": "600519",
    "fields": "operating_cash_flow,market_cap",
    "calculators": "implied_growth",
    "calculator_config": {
        "implied_growth": {
            "wacc": 0.08,
            "g_terminal": 0.02,
        }
    }
})
```

### 2. 调用多个计算器

```python
result = vi_handle("query", {
    "symbol": "600519",
    "fields": "all",
    "calculators": "implied_growth,peg,dcf",
})
```

## 开发规范

1. **文件命名**：必须以 `calc_` 开头
2. **必需字段**：准确声明 `REQUIRED_FIELDS`，缺少字段时计算器会被跳过
3. **错误处理**：不要抛出异常，返回空字典 `{}`
4. **幂等性**：相同输入应产生相同输出
5. **类型提示**：使用 `dict[str, dict[int, Any]]` 等类型提示

## 内置计算器

| 名称 | 描述 | 必需字段 |
|------|------|----------|
| `implied_growth` | 隐含增长率（DCF 反推） | operating_cash_flow, market_cap |

## 相关文档

- [vi_core 命令](../vi_core/README.md)
- [Calculator 示例](../calculators/)
