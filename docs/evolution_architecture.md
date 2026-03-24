# Acorn 演化系统架构

## 概述

当系统遇到无法处理的能力时，自动触发进化流程，让 LLM Agent 帮忙补全能力。

**核心问题：** 如何让系统知道自己缺了什么，并优雅地请求扩展？

---

## 核心流程

```
用户请求不存在的计算器
         │
         ▼
┌─────────────────────────────────────────────┐
│  1. 业务插件发现能力缺失                      │
│     发布 EVO_CAPABILITY_MISSING 事件         │
└─────────────────────┬───────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────┐
│  2. EvoManager 订阅事件                      │
│     记录缺失 → 调用 Hook 获取进化规范         │
└─────────────────────┬───────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────┐
│  3. 打印进化规范                            │
│     EVOLUTION_NEEDED + 代码模板             │
└─────────────────────────────────────────────┘
```

---

## 事件机制

### 事件常量定义

```python
# acorn-events/src/acorn_events/__init__.py
class AcornEvents:
    # 系统生命周期
    SYS_STARTUP = "sys.startup"
    SYS_PLUGIN_LOADED = "sys.plugin.loaded"
    
    # 演化相关
    EVO_CAPABILITY_MISSING = "evo.capability.missing"
    EVO_START = "evo.start"
    EVO_SUCCESS = "evo.success"
    EVO_FAILED = "evo.failed"
```

### 发布事件

```python
from acorn_events import EventBus, AcornEvents

# 发布能力缺失事件
event_bus.publish(
    AcornEvents.EVO_CAPABILITY_MISSING,
    sender=self,  # 谁发现的
    capability_type="calculator",  # 什么类型
    name="pe_ratio",  # 具体名称
    context={"symbol": "600519"}  # 上下文
)
```

### 订阅事件

```python
@EventBus.on(AcornEvents.EVO_CAPABILITY_MISSING)
def on_capability_missing(event_type, sender, **kwargs):
    capability_type = kwargs.get("capability_type")
    name = kwargs.get("name")
    context = kwargs.get("context", {})
```

---

## Hook 机制

### 为什么需要 Hook？

事件机制解决"通知"问题，但解决不了"谁有能力提供进化规范"的问题。

Hook 让插件声明："这个类型的能力缺失，我知道怎么生成规范。"

### get_evolution_spec Hook

```python
# acorn-core/src/acorn_core/specs.py
class EvolutionSpec:
    @hookspec(firstresult=True)
    def get_evolution_spec(
        self,
        capability_type: str,
        name: str,
        context: dict | None = None,
    ) -> str | None:
        """返回进化规范，或 None 表示不关心"""
```

**参数说明：**
- `capability_type`: 能力类型，如 `"calculator"`, `"field"`, `"command"`
- `name`: 具体名称，如 `"pe_ratio"`, `"npcf_ratio"`
- `context`: 上下文信息（可选）

**返回值：**
- `None`: 不关心这个类型，或已支持
- `str`: 进化规范（给 LLM 的 prompt）

**firstresult=True**: 只取第一个非 None 结果，实现自动过滤。

---

## 如何扩展

### 场景：添加新的能力类型

假设你创建了一个新的领域插件 `risk-analyzer`，想要支持 `risk_score` 指标的进化。

#### 1. 定义事件发布（业务插件）

```python
# risk_analyzer/plugin.py
from acorn_events import EventBus, AcornEvents

class RiskAnalyzer:
    def __init__(self):
        self._event_bus = EventBus()
    
    def calculate_risk(self, symbol: str, indicators: list[str]):
        for indicator in indicators:
            if not self._has_indicator(indicator):
                # 发布能力缺失事件
                self._event_bus.publish(
                    AcornEvents.EVO_CAPABILITY_MISSING,
                    sender=self,
                    capability_type="risk_indicator",
                    name=indicator,
                    context={"symbol": symbol}
                )
    
    def _has_indicator(self, name: str) -> bool:
        return name in self._supported_indicators
```

#### 2. 实现 Hook（提供进化规范）

```python
# risk_analyzer/plugin.py
from acorn_core.specs import hookimpl

class RiskAnalyzer:
    @hookimpl
    def get_evolution_spec(
        self,
        capability_type: str,
        name: str,
        context: dict | None = None,
    ) -> str | None:
        """实现 Hook，提供 risk_indicator 类型的进化规范"""
        
        # 只关心 risk_indicator 类型
        if capability_type != "risk_indicator":
            return None
        
        # 检查是否已支持
        if self._has_indicator(name):
            return None
        
        # 返回进化规范
        return f'''要创建风险指标 `{name}`，请按以下格式提供代码：

```python
REQUIRED_FIELDS = ["field_a", "field_b"]

def calculate(data, config):
    """
    计算风险指标
    
    Args:
        data: dict[str, pd.Series] - 字段数据
        config: dict - 用户配置
        
    Returns:
        pd.Series - 计算结果
    """
    return (data["field_a"] - data["field_b"]) / data["field_b"]
```
'''
```

#### 3. 注册插件

```toml
# risk_analyzer/pyproject.toml
[project.entry-points."yapex.acorn.plugins"]
risk = "risk_analyzer.plugin:plugin"
```

---

## 完整示例：CalculatorEngine

这是实际实现，展示了如何处理 `calculator` 类型的能力缺失。

```python
# vi_calculators/__init__.py
from acorn_core.specs import hookimpl

class CalculatorEngine:
    @hookimpl
    def get_evolution_spec(
        self,
        capability_type: str,
        name: str,
        context: dict | None = None,
    ) -> str | None:
        if capability_type != "calculator":
            return None  # 不关心其他类型
        
        if self._has_calculator(name):
            return None  # 已支持
        
        # 不支持，返回进化规范
        return f'''要创建计算器 `{name}`，请按以下格式提供代码：

```python
REQUIRED_FIELDS = ["field_a", "field_b"]

def calculate(data, config):
    """
    计算说明
    
    Args:
        data: dict[str, pd.Series] - 字段数据
        config: dict - 用户配置
        
    Returns:
        pd.Series - 计算结果
    """
    return data["field_a"] / data["field_b"]
```

可用字段：
- operating_cash_flow = 经营现金流
- net_profit = 净利润
- total_assets = 总资产
- market_cap = 市值
'''
```

---

## EvoManager 工作原理

EvoManager 是核心插件，负责：
1. 订阅 `EVO_CAPABILITY_MISSING` 事件
2. 通过 Hook 获取进化规范
3. 打印规范供 LLM 读取

```python
# acorn-core/src/acorn_core/plugins/evo_manager.py
class EvoManager:
    def __init__(self, pm: pluggy.PluginManager, event_bus: EventBus):
        self._pm = pm
        self._event_bus = event_bus
        self.capability_missing = []
    
    @hookimpl
    def on_load(self):
        # 订阅事件
        self._event_bus.on(AcornEvents.EVO_CAPABILITY_MISSING)(
            self._on_capability_missing
        )
    
    def _on_capability_missing(self, event_type, sender, **kwargs):
        capability_type = kwargs.get("capability_type")
        name = kwargs.get("name")
        context = kwargs.get("context")
        
        # 记录
        self.capability_missing.append({
            "capability_type": capability_type,
            "name": name,
            "context": context,
        })
        
        # 获取进化规范
        spec = self._get_evolution_spec(capability_type, name, context)
        
        if spec:
            print(f"\n{'='*60}")
            print(f"EVOLUTION_NEEDED: {capability_type}/{name}")
            print(f"{'='*60}")
            print(spec)
            print(f"{'='*60}\n")
    
    def _get_evolution_spec(self, capability_type, name, context):
        # 通过 Hook 获取规范
        for plugin in self._pm.get_plugins():
            if hasattr(plugin, "get_evolution_spec"):
                spec = plugin.get_evolution_spec(capability_type, name, context)
                if spec:
                    return spec
        return None
```

---

## 架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                         用户 / LLM                               │
└─────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                     业务插件 (domain)                            │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐     │
│  │ ViCorePlugin  │  │RiskAnalyzer   │  │OtherPlugins   │     │
│  │               │  │               │  │               │     │
│  │ 发布事件:     │  │ 发布事件:     │  │ 发布事件:     │     │
│  │ capability_  │  │ capability_   │  │ capability_   │     │
│  │ missing       │  │ missing       │  │ missing       │     │
│  └───────────────┘  └───────────────┘  └───────────────┘     │
└─────────────────────────────────────────────────────────────────┘
                                 │
                    EVO_CAPABILITY_MISSING 事件
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                    核心框架 (acorn-core)                         │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  EvoManager                                               │   │
│  │  • 订阅事件                                               │   │
│  │  • 调用 Hook 获取规范                                      │   │
│  │  • 打印进化提示                                           │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                 │                               │
│                        Hook 调用 (firstresult)                  │
│                                 ▼                               │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Hook 实现                                               │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │   │
│  │  │Calculator   │  │RiskAnalyzer│  │OtherPlugins │    │   │
│  │  │Engine       │  │            │  │            │    │   │
│  │  │get_evo_spec │  │get_evo_spec│  │get_evo_spec│    │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘    │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 扩展机制对比

| 机制 | 时机 | 用途 | 示例 |
|------|------|------|------|
| **entry_points** | 打包时 | CLI 子命令 | `acorn vi query` |
| **pluggy hooks** | 运行时 | 能力发现 | `vi_list_calculators` |
| **event_bus** | 运行时 | 解耦通知 | `EVO_CAPABILITY_MISSING` |
| **get_evolution_spec** | 运行时 | 能力补全 | CalculatorEngine |

---

## 文件结构

```
acorn-core/src/acorn_core/
├── specs.py              # EvolutionSpec Hook 定义
├── kernel.py             # 加载 EvoManager
└── plugins/
    └── evo_manager.py    # EvoManager 实现

acorn-events/src/acorn_events/
└── __init__.py           # AcornEvents 常量

业务插件/
├── vi_calculators/       # 实现 get_evolution_spec
└── vi_core/             # 发布 EVO_CAPABILITY_MISSING
```

---

## 下一步

- [ ] EvoManager → LLM 通信（自动触发进化）
- [ ] 异步请求处理（aiojobs）
- [ ] 进化结果验证和回滚
