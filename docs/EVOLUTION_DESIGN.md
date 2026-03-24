# Acorn 演化系统设计文档

## 背景

acorn-agent 需要支持并发请求处理和异步进化操作，避免请求之间互相阻塞。

---

## 一、扩展机制规范

### 1. 三种扩展机制

| 机制 | 扩展时机 | 用途 | 特点 |
|------|---------|------|-------|
| **entry_points** | 打包时静态 | CLI 子命令扩展 | 独立 Typer app |
| **pluggy hooks** | 运行时动态 | 核心能力扩展 | 同步返回结果 |
| **event_bus** | 运行时动态 | 跨插件通信 | 解耦、观察者模式 |

### 2. 决策树

```
需要扩展系统能力？
         │
         ├── 是，用户需要直接交互的子命令？
         │         └── entry_points (pyproject.toml)
         │
         ├── 是，需要同步返回结果？
         │         └── pluggy hooks (vi_hookspec)
         │
         └── 只是想知道某事发生了？
                   └── event_bus (AcornEvents 常量)
```

### 3. 事件常量命名规范

所有事件使用 `AcornEvents` 常量定义，禁止硬编码字符串。

**命名规范：**
- `sys.*` - 系统生命周期事件（核心框架）
- `evo.*` - 演化相关事件（核心框架）
- **注意**：核心框架不定义业务特定事件（如 `vi.*`），业务插件的能力缺失统一使用 `EVO_CAPABILITY_MISSING`

```python
from acorn_events import EventBus, AcornEvents

# 订阅
@EventBus.on(AcornEvents.EVO_CAPABILITY_MISSING)
def on_capability_missing(event_type, sender, **kwargs):
    ...

# 发布
EventBus.publish(
    AcornEvents.EVO_CAPABILITY_MISSING,
    sender=self,
    capability_type="calculator",
    name="npcf_ratio"
)
```

---

## 二、事件常量定义

### acorn_events（核心框架）

核心框架只定义系统级事件，不依赖任何业务概念：

```python
class AcornEvents:
    # ─────────────────────────────────────────────────────────────────────
    # 系统生命周期事件 (sys.*)
    # ─────────────────────────────────────────────────────────────────────
    
    SYS_STARTUP = "sys.startup"              # 系统启动完成
    SYS_SHUTDOWN = "sys.shutdown"            # 系统关闭
    SYS_PLUGIN_LOADED = "sys.plugin.loaded"  # 插件加载完成
    SYS_PLUGIN_UNLOADED = "sys.plugin.unloaded"  # 插件卸载
    
    # ─────────────────────────────────────────────────────────────────────
    # 演化相关事件 (evo.*)
    # ─────────────────────────────────────────────────────────────────────
    
    EVO_CAPABILITY_MISSING = "evo.capability.missing"  # 能力缺失（通用）
    EVO_REQUEST = "evo.request"            # 进化请求
    EVO_START = "evo.start"                # 进化开始
    EVO_SUCCESS = "evo.success"            # 进化成功
    EVO_FAILED = "evo.failed"              # 进化失败
    EVO_CONFLICT = "evo.conflict"          # 进化冲突
    EVO_QUEUED = "evo.queued"              # 进化已入队
    EVO_COMMITTED = "evo.committed"        # 固化完成
```

### 业务插件（vi_core）

**业务插件不定义自己的事件常量**。当业务插件发现能力缺失时，统一发送 `EVO_CAPABILITY_MISSING` 事件：

```python
# vi_core/plugin.py
from acorn_events import AcornEvents

# 字段缺失 → 发送通用能力缺失事件
event_bus.publish(
    AcornEvents.EVO_CAPABILITY_MISSING,
    sender=self,
    capability_type="field",
    name="npcf_ratio",
    context={"symbol": "600519"}
)

# 计算器缺失 → 发送通用能力缺失事件
event_bus.publish(
    AcornEvents.EVO_CAPABILITY_MISSING,
    sender=self,
    capability_type="calculator",
    name="implied_growth",
    context={"symbol": "600519"}
)
```

---

## 三、CalculatorEngine 重命名

### 之前
```python
class CalculatorLoaderPlugin(CalculatorSpec):
    ...
plugin = CalculatorLoaderPlugin()
```

### 之后
```python
class CalculatorEngine(CalculatorSpec):
    """
    Calculator 引擎
    
    职责：
    - 发现和加载计算器
    - 运行计算器
    - 提供进化规范（通过 Hook）
    """
    ...

plugin = CalculatorEngine()
```

---

## 四、进化机制设计

### 1. 核心流程

```
1. 用户 → LLM → 框架：查询某财务指标
2. 框架 → ViCorePlugin：要求计算该指标
3. ViCorePlugin 发现缺乏能力 → 发送 EVO_CAPABILITY_MISSING 事件（带身份标识）
4. EvoManager 响应事件 → 通过 Hook 询问所有插件
5. 所有插件响应，但消息被过滤 → 只有相关插件返回规范
6. EvoManager 拿到 Prompt → 直接发送给 LLM
7. LLM 多轮交互 → 部署完成新计算器
```

### 2. 架构图

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           用户 + LLM                                    │
└─────────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         Acorn 框架核心                                   │
│                                                                         │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────────┐ │
│  │  ViCorePlugin   │    │   EvoManager    │    │   Plugin Manager    │ │
│  │  (业务插件)     │───▶│   (核心插件)    │◀───│   (Hook 调度)        │ │
│  │                 │    │                 │    │                     │ │
│  │  发现能力缺失   │    │  收集进化规范   │    │  分发 Hook 调用      │ │
│  │  发布事件       │    │                 │    │                     │ │
│  └────────┬────────┘    └────────┬────────┘    └──────────┬──────────┘ │
│           │                      │                        │            │
└───────────┼──────────────────────┼────────────────────────┼────────────┘
            │                      │                        │
            ▼                      ▼                        ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                            插件层                                        │
│                                                                         │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────┐ │
│  │ CalculatorEngine│  │   Field Plugin  │  │   Other Plugins...     │ │
│  │                 │  │                 │  │                         │ │
│  │ get_evolution_  │  │ get_evolution_  │  │   get_evolution_       │ │
│  │ spec (hook)     │  │ spec (hook)     │  │   spec (hook)          │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
```

### 3. Hook 设计

**核心原则**：框架不依赖插件，插件通过 Hook 注册能力。

**Hook spec 定义位置**：`acorn-core/src/acorn_core/specs.py`（框架核心）

```python
# acorn_core/specs.py
from pluggy import HookspecMarker

hookspec = HookspecMarker("evo")

@hookspec(firstresult=True)  # firstresult=True 只取第一个非 None 结果
def get_evolution_spec(
    capability_type: str,
    name: str,
    context: dict | None = None
) -> str | None:
    """
    询问插件是否支持某能力，不支持则返回进化规范
    
    Args:
        capability_type: 能力类型，如 "calculator", "field", "command" 等
            - 框架不定义具体类型，由各业务领域自行约定
            - 但建议使用通用命名（如 "calculator" 而非 "vi_calculator"）
        name: 具体名称
        context: 可选的上下文信息
        
    Returns:
        None - 支持此能力或不关心此类型
        str - 不支持，返回进化规范（给 LLM 的 prompt）
    """
```

**为什么 Hook spec 定义在框架核心？**
- EvoManager 是核心框架插件，负责调用 Hook 获取进化规范
- Hook spec 应该由"调用 Hook 的一方"定义，而不是"实现 Hook 的一方"
- 依赖方向：业务插件 → 框架核心（实现 Hook），而非框架 → 业务插件

**为什么命名不带 `vi` 前缀？**
- `get_evolution_spec` 是框架级通用机制，不依赖任何业务概念
- 其他业务模块（非 VI 领域）也可以复用这个进化机制
- 业务插件实现时，在自己的 Hook impl 中处理业务逻辑即可

### 4. CalculatorEngine 实现 Hook

```python
# vi_calculators/__init__.py
from pluggy import HookimplMarker

# 注意：使用框架的 hookimpl marker（来自 acorn_core.specs）
from acorn_core.specs import hookimpl

class CalculatorEngine(CalculatorSpec):
    ...
    
    @hookimpl
    def get_evolution_spec(
        self,
        capability_type: str,
        name: str,
        context: dict | None = None
    ) -> str | None:
        """
        询问是否支持某计算器，如果不支持，返回进化规范
        
        Returns:
            None - 支持此计算器或不关心此类型
            str - 不支持，返回进化规范（给 LLM 的 prompt）
        """
        if capability_type != "calculator":
            return None  # 不关心其他类型
        
        if self._has_calculator(name):
            return None  # 已支持
        
        # 不支持，返回进化规范
        return self._build_evolution_prompt(name)
    
    def _build_evolution_prompt(self, name: str) -> str:
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
    return data["field_a"] / data["field_b"].replace(0, float('nan'))
```

字段映射参考：
- operating_cash_flow = 经营现金流
- net_profit = 净利润
- total_assets = 总资产
- total_equity = 净资产
- interest_bearing_debt = 有息负债
- ebitda = 息税折旧摊销前利润
- market_cap = 市值
- basic_eps = 每股收益
- book_value_per_share = 每股净资产
'''
```

### 5. 框架调用 Hook

```python
# acorn_core/plugins/evo_manager.py
class EvoManager:
    def _get_evolution_spec(
        self,
        capability_type: str,
        name: str,
        context: dict | None = None
    ) -> str | None:
        """
        通过 Hook 获取进化规范
        
        Returns:
            None - 没有插件能提供进化规范
            str - 进化规范（给 LLM 的 prompt）
        """
        pm = self._get_plugin_manager()
        if not pm:
            return None
        
        # 通过 Hook 调用，firstresult=True 表示只取第一个非 None 结果
        return pm.hook.get_evolution_spec(
            capability_type=capability_type,
            name=name,
            context=context
        )
```

---

## 五、事件驱动的进化生命周期

### 1. 完整流程

```
用户请求 npcf_ratio
         │
         ▼
┌─────────────────────────────────────────────────────────────────────┐
│  ViCorePlugin._query()                                             │
│  → 检查字段是否存在                                                 │
│  → 发现字段缺失                                                     │
└─────────────────────────────┬───────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│  发布 EVO_CAPABILITY_MISSING                                        │
│  {                                                                  │
│    sender: ViCorePlugin,                                            │
│    capability_type: "field",                                        │
│    name: "npcf_ratio",                                              │
│    context: {"symbol": "600519"}                                    │
│  }                                                                  │
└─────────────────────────────┬───────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│  EvoManager._on_capability_missing()                               │
│  → 记录能力缺失                                                     │
│  → 打印进化提示（供 LLM 读取）                                       │
│  → TODO: 通过 Hook 获取进化规范                                      │
│  → TODO: 发送给 LLM                                                 │
└─────────────────────────────┬───────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│  TODO: EvoManager → LLM：发送进化规范                               │
│  TODO: LLM 多轮交互 → 生成代码 → 部署                                │
│  TODO: 发布 EVO_SUCCESS / EVO_FAILED                                │
└─────────────────────────────────────────────────────────────────────┘
```

### 2. EvoManager 设计

```python
# acorn_core/plugins/evo_manager.py
class EvoManager:
    """
    进化管理器 - 赋予 Acorn 求生欲的干细胞插件
    
    职责：
    - 订阅能力缺失事件
    - 记录能力缺失历史
    - TODO: 通过 Hook 获取进化规范
    - TODO: 与 LLM 交互完成进化
    - TODO: 发布进化生命周期事件
    """
    
    def __init__(self, event_bus: EventBus | None = None):
        self.capability_missing: list[dict] = []  # 能力缺失记录
        self.max_log = 100
        self._event_bus = event_bus
    
    @hookimpl
    def on_load(self) -> None:
        """初始化时订阅系统级演化事件"""
        if self._event_bus is None:
            from acorn_events import EventBus
            self._event_bus = EventBus()
        
        # 只订阅系统级事件，不依赖业务概念
        from acorn_events import AcornEvents
        self._event_bus.on(AcornEvents.EVO_CAPABILITY_MISSING)(
            self._on_capability_missing
        )
    
    def _on_capability_missing(
        self,
        event_type: str,
        sender: Any,
        **kwargs: Any
    ) -> None:
        """
        处理能力缺失事件
        
        payload:
        - capability_type: "field" 或 "calculator"
        - name: 能力名称
        - context: 上下文信息
        - sender: 事件发布者（身份标识）
        """
        capability_type = kwargs.get("capability_type", "unknown")
        name = kwargs.get("name", "unknown")
        context = kwargs.get("context", {})
        
        # 记录能力缺失
        self.capability_missing.append({
            "capability_type": capability_type,
            "name": name,
            "context": context,
            "sender": str(sender),
        })
        if len(self.capability_missing) > self.max_log:
            self.capability_missing = self.capability_missing[-self.max_log:]
        
        # 打印进化提示（供 LLM 读取）
        print(f"\n{'='*60}")
        print(f"EVO_CAPABILITY_MISSING: {capability_type}/{name}")
        print(f"{'='*60}\n")
        
        # TODO: 完整进化流程
        # 1. 通过 Hook 获取进化规范
        # spec = self._get_evolution_spec(capability_type, name, context)
        # 2. 发布 EVO_START
        # 3. 发送给 LLM
        # 4. 发布 EVO_SUCCESS / EVO_FAILED
```

### 3. 身份标识与过滤机制

**身份标识**：每个模块发送事件时标明 `sender`。

```python
# 发布能力缺失事件
event_bus.publish(
    AcornEvents.EVO_CAPABILITY_MISSING,
    sender=self,  # 标识是哪个模块
    capability_type="calculator",
    name="npcf_ratio",
    context={"symbol": "600519"}
)
```

**过滤机制**：
1. Hook 使用 `firstresult=True`，只取第一个非 None 结果
2. 最相关的插件（如 CalculatorEngine 对 calculator 类型）返回规范
3. 其他插件返回 None，被自动过滤

### 4. 冲突检测

如果多个插件对同一能力类型都返回规范，说明设计有问题：
- 需要发出 `EVO_CONFLICT` 警告
- 使用第一个结果继续（firstresult 机制）

---

## 六、ViCorePlugin 能力缺失处理

### 1. 字段缺失

```python
# vi_core/plugin.py
def _query(self, args):
    symbol = args.get("symbol")
    fields_str = args.get("fields")
    
    # 解析字段
    requested_fields = {"roe", "npcf_ratio"}
    
    # 获取系统标准字段（通过 Hook）
    standard_fields = set()
    for result in pm.hook.vi_fields():
        standard_fields.update(result.get("fields", {}).keys())
    
    # 获取 Provider 支持的字段（通过 Hook）
    provider_fields = set()
    for result in pm.hook.vi_supported_fields():
        provider_fields.update(result)
    
    # 检查缺失的字段
    unsupported = requested_fields - standard_fields  # 系统不知道这个字段
    unfilled = requested_fields & (standard_fields - provider_fields)  # Provider 不支持
    
    # 发布能力缺失事件（统一使用 EVO_CAPABILITY_MISSING）
    if unsupported or unfilled:
        missing_fields = list(unsupported | unfilled)
        event_bus.publish(
            AcornEvents.EVO_CAPABILITY_MISSING,
            sender=self,
            capability_type="field",
            name=",".join(missing_fields),
            context={
                "symbol": symbol,
                "unsupported": list(unsupported),
                "unfilled": list(unfilled)
            }
        )
    
    # 继续处理...
```

### 2. 计算器缺失

```python
# vi_core/plugin.py
def _run_calculators(self, df, calculator_names, config):
    # 获取可用计算器列表（通过 Hook）
    calc_list = pm.hook.vi_list_calculators()
    calc_registry = {c["name"]: c for c in calc_list}
    
    results = {}
    for calc_name in calculator_names:
        if calc_name not in calc_registry:
            # 计算器不存在！
            
            # 发布能力缺失事件
            event_bus.publish(
                AcornEvents.EVO_CAPABILITY_MISSING,
                sender=self,
                capability_type="calculator",
                name=calc_name,
                context={"symbol": df.index[0] if len(df) > 0 else None}
            )
            
            # TODO: 获取进化规范（通过 Hook）
            # spec = self._get_evolution_spec("calculator", calc_name)
            # if spec:
            #     print(f"EVOLUTION_NEEDED: {calc_name}")
            #     print(spec)
            continue
        
        # 运行计算器（通过 Hook）
        result = pm.hook.vi_run_calculator(
            name=calc_name,
            data=df,
            config=config
        )
        results[calc_name] = result
    
    return results
```

---

## 七、并发架构设计（TODO）

### 1. 问题

```
当前架构（同步）：

请求 A (查询计算中...) ──────────────────────────────────────
                          ↓
                     阻塞等待...
                          ↓
请求 B (进化验证) ← 必须等 A 完成
```

### 2. 解决方案：aiojobs

使用 aiojobs 实现并发处理（后续实现）。

---

## 八、后续改造任务

### 高优先级（P0）

- [x] 1. 定义事件常量（`sys.*`、`evo.*` 前缀）
- [x] 2. 移除业务特定事件，统一使用 `EVO_CAPABILITY_MISSING`
- [x] 3. EvoManager 订阅 `EVO_CAPABILITY_MISSING`
- [x] 4. 定义 `get_evolution_spec` Hook（firstresult=True，在 acorn_core/specs.py）
- [x] 5. CalculatorEngine 实现 Hook（使用框架 hookimpl，方法签名包含 capability_type）
- [x] 6. EvoManager 通过 Hook 获取进化规范

### 中优先级（P1）

- [ ] 7. EvoManager → LLM 通信
- [ ] 8. 实现异步请求处理（aiojobs）
- [ ] 9. 实现 `EVO_START/SUCCESS/FAILED` 事件发布

### 中优先级（P1）

- [ ] 7. EvoManager → LLM 通信
- [ ] 8. 实现异步请求处理（aiojobs）
- [ ] 9. 实现 `EVO_START/SUCCESS/FAILED` 事件发布

### 低优先级（P2）

- [ ] 10. 实现 `EVO_CONFLICT` 冲突检测
- [ ] 11. 实现进化队列和后台处理
- [ ] 12. 实现 Future 模式供外部查询
- [ ] 13. 添加超时控制
- [ ] 14. 实现优雅关闭

---

## 九、文件清单

### 已完成的修改

```
acorn-events/src/acorn_events/
└── __init__.py        # 事件常量（sys.*、evo.*）

acorn-core/src/acorn_core/
├── specs.py           # get_evolution_spec Hook 定义（EvolutionSpec）
└── kernel.py          # Kernel 直接注册 EvoManager

acorn-core/src/acorn_core/plugins/
└── evo_manager.py     # EvoManager 订阅事件 + 调用 Hook 获取进化规范

value-investment-plugin/vi_core/src/vi_core/
└── plugin.py          # 发送 EVO_CAPABILITY_MISSING

value-investment-plugin/vi_calculators/vi_calculators/
└── __init__.py        # CalculatorEngine 实现 get_evolution_spec Hook
```

### 待修改的文件

```
value-investment-plugin/vi_core/src/vi_core/
└── plugin.py          # （可选）通过 Hook 获取进化规范
```

**注意**：`get_evolution_spec` Hook 已定义在 `acorn-core/src/acorn_core/specs.py`（框架核心）

**注意**：`get_evolution_spec` Hook 已定义在 `acorn-core/src/acorn_core/specs.py`（框架核心）

---

## 十、参考资源

- aiojobs: https://github.com/aio-libs/aiojobs
- asyncio.Queue: https://docs.python.org/3/library/asyncio-queue.html
- asyncio.TaskGroup: https://docs.python.org/3/library/asyncio-task.html#taskgroups
- pluggy: https://github.com/pytest-dev/pluggy

---

## 十一、讨论纪要

### 2024-xx-xx: 演化机制设计讨论（更新）

**关键决策：**

1. **核心框架不依赖业务概念**
   - acorn_events 只定义 `sys.*` 和 `evo.*` 事件
   - 不定义 `vi.*` 等业务特定事件
   - 业务插件的能力缺失统一使用 `EVO_CAPABILITY_MISSING`

2. **Hook spec 定义在框架核心（acorn_core/specs.py）**
   - 原因：EvoManager 是核心框架插件，负责调用 Hook
   - Hook spec 应该由"调用 Hook 的一方"定义，而不是"实现 Hook 的一方"
   - 依赖方向：业务插件 → 框架核心（实现 Hook），而非框架 → 业务插件

3. **Hook 命名不带业务前缀**
   - 使用 `get_evolution_spec` 而非 `vi_get_evolution_spec`
   - 这是框架级通用机制，不依赖任何业务概念
   - 其他业务模块（非 VI 领域）也可以复用这个进化机制

4. **身份标识机制**
   - 每个模块发送事件时标明 `sender`
   - 用于追踪和调试

5. **过滤机制**
   - Hook 使用 `firstresult=True`
   - 最相关的插件返回规范，其他返回 None
   - 天然实现过滤，无需额外逻辑

6. **Evolution Manager 直接通信 LLM**
   - 不输出规范等待外部处理
   - 直接发送给 LLM 完成多轮交互
   - 进化完成后通知主 agent

7. **进化应该异步执行**
   - 使用 aiojobs 实现并发
   - 避免阻塞其他请求

**待定问题：**
- [ ] 进化完成后如何通知主 agent？
- [ ] 进化队列是否需要持久化？
- [ ] Future 模式如何暴露给外部？
