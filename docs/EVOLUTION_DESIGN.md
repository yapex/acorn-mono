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

### 3. 事件常量

所有事件使用 `AcornEvents` 常量定义，禁止硬编码字符串：

```python
from acorn_events import EventBus, AcornEvents

# 订阅
@EventBus.on(AcornEvents.CALCULATOR_EXTENSION_NEEDED)
def on_calc_needed(event_type, sender, **kwargs):
    ...

# 发布
EventBus.publish(AcornEvents.FIELD_UNSUPPORTED, sender=self, symbol="600519", fields=[...])
```

可用事件：

| 常量 | 事件名 | 触发时机 |
|------|--------|---------|
| `FIELD_UNSUPPORTED` | `vi.field.unsupported` | 字段不在标准定义中 |
| `FIELD_UNFILLED` | `vi.field.unfilled` | Provider 无法提供字段 |
| `CALCULATOR_EXTENSION_NEEDED` | `calculator.extension_needed` | 计算器不存在 |
| `CALCULATOR_REGISTERED` | `calculator.registered` | 计算器已注册 |
| `SYSTEM_STARTUP` | `system.startup` | 系统启动完成 |
| `SYSTEM_SHUTDOWN` | `system.shutdown` | 系统关闭 |
| `PLUGIN_LOADED` | `acorn.plugin.loaded` | 插件加载完成 |

---

## 二、CalculatorEngine 重命名

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
    - 提供进化规范
    """
    ...

plugin = CalculatorEngine()
```

---

## 三、进化机制设计

### 1. 核心概念

```
用户请求 npcf_ratio
         │
         ▼
┌─────────────────────────────────────────────────────────────────────┐
│  系统问 CalculatorEngine: "你能算 npcf_ratio 吗？"                 │
│                                                                     │
│  CalculatorEngine:                                                   │
│  "不能算，但进化规范是：'创建计算器请用以下格式...'"               │
└─────────────────────────────┬───────────────────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│  系统发布进化请求，等待外部处理                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### 2. get_evolution_spec 方法

每个有能力扩展的插件实现此方法：

```python
def get_evolution_spec(self, capability_type: str, name: str) -> str | None:
    """
    询问是否支持某能力，如果不支持，返回进化规范
    
    Args:
        capability_type: 能力类型，如 "calculator", "field"
        name: 具体名称
        
    Returns:
        None - 支持此能力
        str - 不支持，返回进化规范（给 LLM 的 prompt）
    """
```

### 3. CalculatorEngine 实现

```python
def get_evolution_spec(self, capability_type: str, name: str) -> str | None:
    if capability_type != "calculator":
        return None
    
    if name in self._calculators:
        return None  # 已支持
    
    # 不支持，返回进化规范
    return '''要创建计算器，请按以下格式提供代码：

```python
REQUIRED_FIELDS = ["field_a", "field_b"]

def calculate(data, config):
    return data["field_a"] / data["field_b"].replace(0, float('nan'))
```

字段映射参考：
- operating_cash_flow = 经营现金流
- net_profit = 净利润
...
'''
```

---

## 四、事件驱动的进化生命周期

### 1. 事件定义

```python
class AcornEvents:
    REQUEST_START = "vi.request.start"        # 请求开始
    REQUEST_END = "vi.request.end"            # 请求结束
    EVOLUTION_CANDIDATE = "evolution.candidate"  # 进化候选
    EVOLUTION_CONFLICT = "evolution.conflict"   # 进化冲突
    EVOLUTION_QUEUED = "evolution.queued"       # 进化已入队
    EVOLUTION_START = "evolution.start"          # 进化开始
    EVOLUTION_SUCCESS = "evolution.success"      # 进化成功
    EVOLUTION_FAILED = "evolution.failed"        # 进化失败
    EVOLUTION_COMMITTED = "evolution.committed"  # 固化完成
```

### 2. 完整流程

```
用户请求 npcf_ratio
         │
         ▼
┌─────────────────────────────────────────────────────────────────────┐
│  REQUEST_START (request_id="xxx")                                  │
└─────────────────────────────┬───────────────────────────────────────┘
                              │
         ┌───────────────────┴───────────────────┐
         ▼                                       ▼
┌─────────────────────┐              ┌─────────────────────┐
│ EVOLUTION_CANDIDATE │              │ EVOLUTION_CANDIDATE │
│ capability_type=    │              │ capability_type=    │
│   "calculator"      │              │   "field"          │
│ name="npcf_ratio"  │              │ name="ocf"         │
└─────────────────────┘              └─────────────────────┘
         │                                       │
         └───────────────────┬───────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│  REQUEST_END (request_id="xxx")                                    │
│         ↓                                                           │
│  EvoManager 收集所有候选 → 调用 get_evolution_spec → 输出 prompt   │
└─────────────────────────────────────────────────────────────────────┘
```

### 3. EvoManager 设计

```python
class EvoManager:
    def __init__(self):
        self.pending = {}  # request_id -> [candidates]
        self.evolution_queue = []
    
    def on_load(self):
        EventBus.on(AcornEvents.REQUEST_START)(self._on_request_start)
        EventBus.on(AcornEvents.EVOLUTION_CANDIDATE)(self._on_evolution_candidate)
        EventBus.on(AcornEvents.REQUEST_END)(self._on_request_end)
        EventBus.on(AcornEvents.EVOLUTION_CONFLICT)(self._on_evolution_conflict)
    
    def _on_evolution_candidate(self, event_type, sender, **kwargs):
        request_id = kwargs["request_id"]
        if request_id not in self.pending:
            self.pending[request_id] = []
        self.pending[request_id].append({
            "capability_type": kwargs["capability_type"],
            "name": kwargs["name"],
            "context": kwargs.get("context")
        })
    
    def _on_request_end(self, event_type, sender, **kwargs):
        request_id = kwargs["request_id"]
        candidates = self.pending.pop(request_id, [])
        
        if not candidates:
            return  # 请求成功，无需进化
        
        # 向插件获取进化规范
        specs = []
        for c in candidates:
            spec = self._get_evolution_spec(c)
            if spec:
                specs.append(spec)
        
        if not specs:
            return
        
        # 检查冲突
        if len(specs) > 1:
            log.warning(f"多个插件响应了同一能力: {candidates}")
            EventBus.publish(AcornEvents.EVOLUTION_CONFLICT, ...)
        
        # 输出进化规范（加上协议说明）
        self._output_evolution_prompt(specs)
    
    def _output_evolution_prompt(self, specs: list[str]):
        """输出进化规范，告诉 LLM 在 subagent 中执行"""
        print("[EVOLUTION_PROTOCOL]")
        print("此进化任务应在 subagent 中异步执行。")
        print("主 agent 可继续响应用户其他请求。")
        print("[/EVOLUTION_PROTOCOL]")
        print()
        for spec in specs:
            print(spec)
```

### 4. 冲突检测

如果多个插件响应同一 capability_type，说明设计有问题：
- 需要发出 `EVOLUTION_CONFLICT` 警告
- 使用第一个结果继续

---

## 五、并发架构设计

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

使用 aiojobs 实现并发处理：

```python
from aiojobs import create_scheduler

class AsyncAcornAgent:
    def __init__(self, max_concurrent: int = 4):
        self.scheduler = None
        self.max_concurrent = max_concurrent
        self.results = {}
        self.pending = {}  # request_id -> status
    
    async def start(self):
        self.scheduler = await create_scheduler(limit=self.max_concurrent)
    
    async def stop(self):
        await self.scheduler.close()
    
    async def submit(self, command: str, args: dict) -> str:
        """提交请求，立即返回 request_id"""
        request_id = str(uuid.uuid4())[:8]
        
        # 发布 REQUEST_START
        EventBus.publish(AcornEvents.REQUEST_START,
                        sender=self,
                        request_id=request_id,
                        command=command)
        
        # 提交任务到调度器
        await self.scheduler.spawn(self._process(request_id, command, args))
        
        return request_id
    
    async def _process(self, request_id: str, command: str, args: dict):
        """处理请求"""
        try:
            result = await self._execute(command, args)
            
            # 发布 REQUEST_END
            EventBus.publish(AcornEvents.REQUEST_END,
                           sender=self,
                           request_id=request_id)
            
            self.results[request_id] = {"status": "done", "data": result}
            return result
            
        except Exception as e:
            self.results[request_id] = {"status": "error", "error": str(e)}
            raise
    
    def get_status(self, request_id: str) -> dict:
        """查询状态（不等待）"""
        return self.results.get(request_id, {"status": "pending"})
    
    async def wait(self, request_id: str, timeout: float = 30) -> dict:
        """等待请求完成"""
        # 等待结果...
```

### 3. 请求流程

```
┌─────────────────────────────────────────────────────────────────────┐
│                        acorn-agent (async)                          │
│                                                                     │
│  ┌──────────────┐                                                  │
│  │  Socket 监听 │                                                  │
│  └──────┬───────┘                                                  │
│         │                                                           │
│         ▼                                                           │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │              aiojobs Scheduler (max_concurrent=4)           │  │
│  │                                                             │  │
│  │   Task 1: vi_query 600519                                  │  │
│  │   Task 2: vi_query 000001                                  │  │
│  │   Task 3: evolution validation                              │  │
│  │   Task 4: status check                                     │  │
│  └──────────────────────────────────────────────────────────────┘  │
│         │                                                           │
│         ▼                                                           │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │              Results Store                                   │  │
│  │              request_id → {status, data}                    │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │              EvoManager                                      │  │
│  │              pending → collect specs → evolution queue       │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 六、后续改造任务

### 高优先级

- [ ] 1. 实现 `get_evolution_spec` hook 在 CalculatorEngine
- [ ] 2. 实现 EvoManager 的事件订阅和处理
- [ ] 3. 添加进化相关事件常量
- [ ] 4. 实现异步请求处理（aiojobs）

### 中优先级

- [ ] 5. 实现 `EVOLUTION_CONFLICT` 冲突检测
- [ ] 6. 实现进化队列和后台处理
- [ ] 7. 添加 `EVOLUTION_START/SUCCESS/FAILED` 事件

### 低优先级

- [ ] 8. 实现 Future 模式供外部查询
- [ ] 9. 添加超时控制
- [ ] 10. 实现优雅关闭

---

## 七、文件清单

### 需要修改的文件

```
acorn-cli/src/acorn_cli/
├── server.py          # 添加异步支持
└── cli.py            # status 命令

acorn-core/src/acorn_core/
├── kernel.py          # 事件发布
├── plugins/
│   └── evo_manager.py  # 进化管理

acorn-events/src/acorn_events/
└── __init__.py        # 添加新事件常量

value-investment-plugin/
├── vi_core/src/vi_core/
│   ├── plugin.py      # 调用 get_evolution_spec
│   └── spec.py        # 添加 EvolutionSpec hook
└── vi_calculators/vi_calculators/
    └── __init__.py    # CalculatorEngine 重命名 + get_evolution_spec
```

### 需要新增的文件

```
.acorn/docs/
└── EVOLUTION_DESIGN.md  # 本文档
```

---

## 八、参考资源

- aiojobs: https://github.com/aio-libs/aiojobs
- asyncio.Queue: https://docs.python.org/3/library/asyncio-queue.html
- asyncio.TaskGroup: https://docs.python.org/3/library/asyncio-task.html#taskgroups

---

## 九、讨论纪要

### 2024-xx-xx: 演化机制设计讨论

**关键决策：**

1. **get_evolution_spec 不是 hook，是插件的直接方法**
   - 原因：pluggy hook 不适合"问一个能力是否支持"的模式
   - 通过 vi_core 遍历插件调用

2. **EvoManager 不知道具体业务**
   - 只订阅通用生命周期事件
   - 具体规范由插件通过 get_evolution_spec 提供

3. **进化应该异步执行**
   - 使用 aiojobs 实现并发
   - 避免阻塞其他请求

4. **多插件响应同一能力是冲突**
   - 需要发出警告
   - 但仍然使用第一个结果继续

**待定问题：**
- [ ] 进化完成后如何通知主 agent？
- [ ] 进化队列是否需要持久化？
- [ ] Future 模式如何暴露给外部？
