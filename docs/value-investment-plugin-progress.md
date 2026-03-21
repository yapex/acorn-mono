# Value Investment Plugin - 开发进展

> 当前进度记录

## 项目结构

```
value-investment-plugin/
├── vi_core/                    # 核心包
│   ├── src/vi_core/
│   │   ├── __init__.py
│   │   ├── spec.py           # pluggy Hook 规范
│   │   ├── fields.py         # 字段类型定义
│   │   └── plugin.py         # pluggy 插件入口
│   └── pyproject.toml
│
├── vi_fields_ifrs/            # IFRS 标准字段插件
│   ├── src/vi_fields_ifrs/
│   │   ├── __init__.py
│   │   └── plugin.py         # 38 个 IFRS 字段
│   └── pyproject.toml
│
├── vi_fields_extension/        # 扩展字段插件
│   ├── src/vi_fields_extension/
│   │   ├── __init__.py       # register_fields() 函数
│   │   └── plugin.py         # pluggy 插件
│   └── pyproject.toml
│
├── provider_tushare/          # Provider 插件（待实现）
├── calculators/                # Calculator 插件（待实现）
│   └── calc_implied_growth.py
│
└── vi_cli/                    # CLI 插件（待实现）
```

## 已完成

### 1. vi_core - 核心框架

**pluggy Hook 规范 (`spec.py`)：**

```python
# 字段注册
def vi_fields(self) -> dict  # 返回 {"source": str, "fields": set, "description": str}

# 字段提供者
def vi_markets(self) -> list[str]      # 支持的市场 ["A", "HK", "US"]
def vi_provides(self) -> list[str]     # 支持的字段
def vi_fetch(symbol, field, years) -> dict | None

# 计算器
def vi_list_calculators(self) -> list[dict]

# 命令
def vi_commands(self) -> list[str]
def vi_handle(command, args) -> dict
```

**已有命令：**
- `list_fields` - 列出所有可用字段
- `query` - 查询数据（待实现）

### 2. vi_fields_ifrs - IFRS 标准字段

38 个国际标准字段：
- 资产负债表：total_assets, total_equity, cash_and_equivalents, ...
- 利润表：total_revenue, net_profit, operating_profit, ...
- 现金流量：operating_cash_flow, capital_expenditure, ...
- 比率：roe, roa, gross_margin, pe_ratio, ...

### 3. vi_fields_extension - 扩展字段机制

**一行代码注册字段：**

```python
from vi_fields_extension import register_fields

register_fields(
    source="my_plugin",
    fields={
        "sector": "所属行业",
        "dividend_yield": "股息率",
    }
)
```

**架构：**
- 维护全局注册表 `_custom_fields`
- pluggy 插件聚合所有注册字段
- 通过 `vi_fields` hook 暴露给系统

## 验证结果

```
Total fields: 76
  ifrs: 38 (IFRS 标准字段)
  extension: 38 (Tushare 扩展字段)
```

## 安装方式

```bash
# 开发模式
uv pip install -e value-investment-plugin/vi_core
uv pip install -e value-investment-plugin/vi_fields_ifrs
uv pip install -e value-investment-plugin/vi_fields_extension

# 通过 entry_points 自动发现
pm.load_setuptools_entrypoints('value_investment.fields')
```

## 扩展点设计经验

### 1. entry_points 写法

```toml
# ❌ 错误
[project.entry-points."value_investment.fields"]
extension = "vi_fields_extension:plugin"

# ✅ 正确
[project.entry-points."value_investment.fields"]
extension = "vi_fields_extension.plugin:plugin"
```

需要 `模块名:对象名`，不能只写模块名。

---

### 2. pluggy 的 hook 发现机制

pluggy 通过 `@hookimpl` 装饰器发现 hook 实现，但需要在 **spec 注册之后** 才能正确识别：

```python
pm = pluggy.PluginManager('value_investment')
pm.add_hookspecs(ValueInvestmentSpecs)  # 先注册 spec
pm.register(plugin)                     # 再注册 plugin
```

---

### 3. 模块导入区别

```python
# 导入 __init__.py
from vi_fields_extension import plugin  # ❌ 可能是 module

# 导入 plugin.py 中的对象
from vi_fields_extension.plugin import plugin  # ✅ 正确
```

---

### 4. 扩展点设计原则

**最小代价扩展：**

```python
# 开发者只需一行
register_fields(source="my", fields={...})

# 系统自动聚合
pm.hook.vi_fields()
```

**关键点：**
- 暴露简单 API
- 内部维护注册表
- 通过 pluggy hook 暴露给系统

---

### 5. 分层设计

```
vi_fields_ifrs (冻结)     → 基础标准（不可修改）
vi_fields_extension (扩展) → Provider 字段（可扩展）
```

职责清晰，易于维护。

---

### 6. pyright 类型检查

IDE 类型检查报错 ≠ 代码运行错误。pyright 需要 `extraPaths` 配置，但 IDE 缓存可能导致误报。

```json
{
  "extraPaths": [
    ".venv/lib/python3.12/site-packages",
    "value-investment-plugin/vi_core/src",
    "value-investment-plugin/vi_fields_ifrs/src",
    "value-investment-plugin/vi_fields_extension/src"
  ]
}
```

---

## 下一步

- [ ] provider_tushare - Tushare 数据提供者
- [ ] calculators - 计算器插件机制
- [ ] vi_cli - 命令行工具
- [ ] query 命令完整实现
- [ ] acorn-agent 集成
