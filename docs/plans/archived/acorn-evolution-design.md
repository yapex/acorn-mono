# Acorn 自我进化系统设计文档

> **文档状态**: 规划中
> **版本**: v0.1.0
> **日期**: 2026-03-23

---

## 一、愿景与定位

### 1.1 项目愿景

让 Acorn 成为一个**具有自我进化能力**的系统，能够在与 LLM Agent 配合时：
- 感知自身的问题和不足
- 自动分析原因并生成解决方案
- 在安全环境下验证和执行改进
- 从经验中学习，避免重复犯错

### 1.2 设计原则

| 原则 | 说明 |
|------|------|
| **渐进式** | 从最小可行场景开始，逐步扩展 |
| **安全优先** | 所有变更都在沙箱中验证，支持回滚 |
| **可解释** | 每次进化都有清晰的推理过程，用户可审查 |
| **人工确认** | 关键变更需要用户确认，不做静默修改 |
| **经验积累** | 知识库记录进化历史，指导未来决策 |

### 1.3 核心理念：MVPD

- **M**inimum 可行的最小场景
- **V**iable 验证可行的方案
- **P**rogressive 渐进式扩展
- **D**ata-driven 数据驱动决策

---

## 二、当前问题与改进方向

### 2.1 现有架构问题

```
❌ 当前的 evo_manager：
- 只是"记录"错误和不支持的字段
- 没有反馈闭环
- 没有改进动作
- 这叫"日志"，不叫"进化"

❌ pluggy 过度使用：
- evo_manager 和 sandbox 不需要被动态替换
- 它们是内置功能，不应该伪装成"插件"
```

### 2.2 正确的设计思路

```
✅ 适合 pluggy 的场景：
1. 数据提供者 - 多个实现，运行时动态发现
2. CLI 命令扩展 - 不同插件贡献不同命令
3. 字段定义扩展 - 不同标准，用户可自定义

❌ 不适合 pluggy 的场景：
1. evo_manager - 本质是内置服务
2. sandbox - 策略模式即可，不需要动态发现
```

---

## 三、完整架构设计

### 3.1 整体架构图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              用户层                                          │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  acorn-cli                                                                  │
│  ├── typer (CLI 框架)                                                        │
│  ├── questionary (交互式 UI)                                                 │
│  └── acorn-core                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  acorn-core                                                                 │
│  ├── pluggy (插件系统)                                                       │
│  ├── acorn-events (事件总线)                                                 │
│  ├── services/ (内置服务)                                                    │
│  │   ├── evolution/  ← 进化系统                                              │
│  │   └── sandbox/    ← 沙箱隔离                                             │
│  └── kernel.py                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Evolution System                                     │
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                         Evolution Agent                                │  │
│  │                       (LLM 驱动的进化代理)                             │  │
│  │                                                                        │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐   │  │
│  │  │   Context   │  │   Reason    │  │    Act      │  │   Learn     │   │  │
│  │  │  收集上下文  │  │   推理决策  │  │   执行改进  │  │   积累经验  │   │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘   │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                      │                                      │
│                    ┌─────────────────┼─────────────────┐                    │
│                    │                 │                 │                    │
│                    ▼                 ▼                 ▼                    │
│  ┌─────────────────────┐ ┌─────────────────────┐ ┌─────────────────────┐   │
│  │    Event Stream     │ │    Knowledge Base   │ │     Sandbox         │   │
│  │    (事件流)         │ │    (知识库)         │ │     (安全沙箱)      │   │
│  │                     │ │                     │ │                     │   │
│  │ • 查询失败          │ │ • 进化历史          │ │ • 测试新代码        │   │
│  │ • 用户反馈          │ │ • Bug 模式          │ │ • 验证变更          │   │
│  │ • 性能瓶颈          │ │ • 最佳实践          │ │ • 回滚机制          │   │
│  │ • 使用模式          │ │ • 决策记录          │ │                     │   │
│  └─────────────────────┘ └─────────────────────┘ └─────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.2 组件职责

| 组件 | 职责 | 类型 |
|------|------|------|
| **EvolutionAgent** | LLM 驱动的决策引擎，分析问题并生成解决方案 | 服务 |
| **EventStream** | 感知系统事件，触发进化流程 | 服务 |
| **KnowledgeBase** | 存储进化经验和历史 | 服务 |
| **Sandbox** | 安全执行代码变更 | 工具 |
| **Verifier** | 验证变更的正确性 | 工具 |

---

## 四、进化闭环设计

### 4.1 核心闭环

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           自我进化闭环                                        │
│                                                                             │
│   ┌─────────┐     ┌─────────┐     ┌─────────┐     ┌─────────┐             │
│   │  感知   │ ──► │  分析   │ ──► │  改进   │ ──► │  验证   │             │
│   │         │     │  (LLM)  │     │  (LLM)  │     │         │             │
│   └─────────┘     └─────────┘     └─────────┘     └─────────┘             │
│        ▲                                                        │         │
│        └────────────────────────────────────────────────────────┘         │
│                          反馈闭环                                            │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 4.2 进化事件类型

```python
EVOLUTION_EVENTS = [
    # 能力缺口
    "vi.field.unsupported",      # 请求了不存在的字段
    "vi.field.unfilled",         # Provider 无法提供
    "vi.calculator.missing",      # 请求了不存在的计算器
    
    # 错误
    "error.runtime",              # 运行时错误
    "error.data_quality",         # 数据质量问题
    
    # 反馈
    "user.feedback.negative",     # 用户负面反馈
    "user.correction",            # 用户修正
    
    # 模式
    "usage.pattern.detected",     # 检测到使用模式
    "usage.query.frequent",       # 高频查询
]
```

---

## 五、核心数据结构

### 5.1 EvolutionContext (进化上下文)

```python
@dataclass
class EvolutionContext:
    """进化的上下文信息"""
    
    # 触发源
    trigger: str                    # "field_missing" | "error" | "feedback" | "pattern"
    
    # 系统状态
    system_state: dict              # 当前加载的插件、可用字段等
    
    # 用户意图
    user_intent: str | None        # LLM 推断的用户意图
    
    # 历史经验
    relevant_experiences: list     # 知识库中相关的历史案例
    
    # 约束条件
    constraints: dict               # 安全边界、不允许的操作等
```

### 5.2 EvolutionDecision (进化决策)

```python
@dataclass
class EvolutionDecision:
    """进化决策"""
    
    action: str                     # "ignore" | "add_field" | "fix_bug" | "optimize"
    feasibility: str                # "HIGH" | "MEDIUM" | "LOW" | "IMPOSSIBLE"
    risk: str                       # "LOW" | "MEDIUM" | "HIGH"
    reasoning: str                  # 决策理由
    confidence: float               # 置信度 0-1
```

### 5.3 EvolutionExperience (进化经验)

```python
@dataclass
class EvolutionExperience:
    """进化经验记录"""
    
    id: str
    trigger: str                    # 触发类型
    context: dict                   # 当时的上下文
    decision: dict                  # 决策内容
    solution: dict                  # 解决方案
    outcome: str                    # "success" | "failed" | "rolled_back"
    outcome_detail: str             # 详细结果
    timestamp: datetime
    
    # 可用于相似度检索的字段
    field_category: str | None      # 字段类别
    error_type: str | None          # 错误类型
```

---

## 六、EvolutionAgent 设计

### 6.1 核心流程

```python
class EvolutionAgent:
    """LLM 驱动的进化代理"""
    
    def __init__(self, llm_client, knowledge_base, sandbox):
        self.llm = llm_client
        self.kb = knowledge_base
        self.sandbox = sandbox
    
    def on_event(self, event_type: str, data: dict):
        """事件触发入口"""
        
        # 1. 收集上下文
        context = self.build_context(event_type, data)
        
        # 2. 推理：是否需要进化？如何进化？
        decision = self.reason(context)
        
        if decision.action == "ignore":
            return
        
        # 3. 生成改进方案
        solution = self.generate_solution(context, decision)
        
        # 4. 在沙箱中验证
        if self.verify(solution):
            # 5. 应用改进
            self.apply(solution)
            
            # 6. 记录到知识库
            self.learn(context, decision, solution)
    
    def reason(self, context: EvolutionContext) -> EvolutionDecision:
        """LLM 推理"""
        prompt = f"""
        系统事件: {context.trigger}
        系统状态: {json.dumps(context.system_state)}
        用户意图: {context.user_intent}
        相关经验: {context.relevant_experiences}
        
        请决定:
        1. 是否需要进化改进？
        2. 如果需要，应该做什么？
        3. 有什么风险？
        """
        return self.llm.decide(prompt)
    
    def generate_solution(self, context, decision) -> Solution:
        """LLM 生成代码/配置变更"""
        prompt = f"""
        任务: {decision.task}
        约束: {context.constraints}
        
        请生成实现代码。
        """
        code = self.llm.generate(prompt)
        return Solution(code=code, type=decision.solution_type)
```

### 6.2 LLM 提示词设计

#### 字段缺失分析提示词

```
你是一个财务分析系统专家。

系统检测到用户请求了一个不存在的字段: {field_name}

可用字段:
{available_fields}

请分析:
1. 这个字段可能的含义是什么？
2. 是否可以用现有字段计算？
3. 如果可以，输出计算公式
4. 如果不可以，输出原因

输出格式:
{
    "analysis": "...",
    "can_calculate": true/false,
    "formula": "计算公式或 null",
    "required_fields": ["需要的字段列表"],
    "confidence": 0-1
}
```

---

## 七、进化场景详述

### 7.1 场景 1: 字段缺失自动补全 (MVP)

```
用户: acorn vi query 600519 --fields "debt_to_ebitda"

当前: ❌ 字段不存在

目标: 
1. 检测到 debt_to_ebitda 缺失
2. LLM 分析：能否用现有字段计算？
3. 生成代码 → 验证 → 注册
4. 返回计算结果
```

**完整流程**:

```
┌──────────────────────────────────────────────────────────────────────────┐
│ 1. 事件触发                                                              │
│    EventBus.publish("vi.field.missing", {                                │
│        symbol: "600519",                                                 │
│        field: "debt_to_ebitda",                                         │
│    })                                                                    │
└──────────────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌──────────────────────────────────────────────────────────────────────────┐
│ 2. EvolutionAgent 接收事件                                               │
│                                                                          │
│    Context:                                                              │
│    - trigger: "field_missing"                                           │
│    - field: "debt_to_ebitda"                                            │
│    - available_fields: ["interest_bearing_debt", "ebitda", ...]         │
└──────────────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌──────────────────────────────────────────────────────────────────────────┐
│ 3. LLM 推理                                                              │
│                                                                          │
│    Decision:                                                             │
│    - action: "add_field"                                                │
│    - feasibility: "HIGH - debt / ebitda 可用现有字段计算"                 │
│    - risk: "LOW - 纯计算字段，无外部依赖"                                │
└──────────────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌──────────────────────────────────────────────────────────────────────────┐
│ 4. LLM 生成代码                                                          │
│                                                                          │
│    # calc_debt_to_ebitda.py                                             │
│    REQUIRED_FIELDS = ["interest_bearing_debt", "ebitda"]                │
│                                                                          │
│    def calculate(data, config):                                          │
│        debt = data["interest_bearing_debt"]                               │
│        ebitda = data["ebitda"]                                           │
│        return debt / ebitda                                              │
└──────────────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌──────────────────────────────────────────────────────────────────────────┐
│ 5. 沙箱验证                                                              │
│                                                                          │
│    Test cases:                                                           │
│    - 已知公司数据 → 验证计算结果                                          │
│    - 边界值测试 (ebitda=0)                                              │
│    - 性能测试                                                            │
│                                                                          │
│    Result: ✅ 通过                                                        │
└──────────────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌──────────────────────────────────────────────────────────────────────────┐
│ 6. 应用 & 学习                                                           │
│                                                                          │
│    - 注册新计算器: vi_register_calculator                                 │
│    - 记录到知识库:                                                        │
│      {                                                                 │
│        "type": "field_added",                                           │
│        "field": "debt_to_ebitda",                                       │
│        "required_fields": ["interest_bearing_debt", "ebitda"],          │
│        "outcome": "success"                                             │
│      }                                                                  │
└──────────────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
下次: acorn vi query 600519 --fields "debt_to_ebitda" ✅
```

### 7.2 场景 2: 数据异常自动修复

```
用户报告: "2020 年的 roe 怎么是负数？这不对吧"

进化过程:
1. 感知: 用户反馈数据异常
2. 分析: 检查原始数据源和计算逻辑
3. 修复: 生成补丁
4. 验证: 重新计算历史数据
5. 学习: 记录此类 bug 模式
```

### 7.3 场景 3: 使用模式学习

```
检测到: 用户频繁执行
  acorn vi query 600519 --fields "roe,roa,debt_ratio,current_ratio"

进化过程:
1. 感知: 检测到高频查询模式
2. 分析: 这是"偿债能力快速检查"场景
3. 改进: 创建预设模板
   acorn vi quick-check 600519
```

### 7.4 场景 4: 性能优化

```
检测到: provider_market_a 查询耗时 > 5s

进化过程:
1. 感知: 性能瓶颈
2. 分析: 某字段计算复杂度过高
3. 优化: 生成缓存策略或简化算法
4. 验证: 对比优化前后性能
5. 应用: 部署优化方案
```

---

## 八、实施路线图

### Phase 0: 清理与重构 (1-2天)

**目标**: 清理过度设计，还原简洁架构

**任务**:
- [ ] 移除 evo_manager 的 pluggy 装饰，改为内核服务
- [ ] 简化 sandbox 为策略模式工具类
- [ ] 清理 yapex.acorn.plugins 入口点

**验收标准**:
- `acorn vi query` 正常工作
- 没有无用的插件层

### Phase 1: MVP - 字段缺失自动补全 (3-5天)

**目标**: 实现最小可行的进化闭环

**任务**:
- [ ] 创建 `acorn-core/src/acorn_core/evolution/` 模块
- [ ] 实现 `EvolutionContext` 数据结构
- [ ] 实现 `FieldMissingHandler` (字段缺失处理器)
- [ ] 集成 LLM 调用 (支持 OpenAI/Claude)
- [ ] 实现沙箱验证
- [ ] 集成知识库记录

**验收标准**:
```bash
# 用户请求不存在的字段
acorn vi query 600519 --fields "debt_to_ebitda"

# 系统自动:
# 1. 检测字段缺失
# 2. LLM 分析并生成代码
# 3. 验证并注册
# 4. 返回计算结果

# 再次请求时直接返回结果
acorn vi query 600519 --fields "debt_to_ebitda"  # ✅ 直接返回
```

### Phase 2: 知识库增强 (2-3天)

**目标**: 让系统从经验中学习

**任务**:
- [ ] 实现 Experience 存储和检索
- [ ] 实现相似案例查找
- [ ] 实现模式提取
- [ ] 添加历史经验展示命令

**验收标准**:
```bash
# 查看进化历史
acorn evolution history

# 查看相似案例
acorn evolution similar --field debt_to_ebitda
```

### Phase 3: 用户交互增强 (2-3天)

**目标**: 提升用户体验和可控性

**任务**:
- [ ] 添加进化预览功能 (变更前确认)
- [ ] 添加人工确认开关
- [ ] 添加进化日志查看
- [ ] 添加回滚命令

**验收标准**:
```bash
# 预览变更
acorn vi query 600519 --fields "new_field" --preview

# 手动确认模式
acorn config set evolution.auto_apply=false
acorn vi query 600519 --fields "new_field"  # 等待确认

# 回滚
acorn evolution rollback --id <experience_id>
```

### Phase 4: 扩展进化场景 (持续)

**目标**: 支持更多进化场景

**任务**:
- [ ] 数据异常检测与修复
- [ ] 使用模式学习与模板生成
- [ ] 性能优化自动化
- [ ] Provider 故障切换

---

## 九、安全设计

### 9.1 风险等级

| 等级 | 说明 | 处理方式 |
|------|------|---------|
| **LOW** | 纯计算字段，无外部依赖 | 自动执行 |
| **MEDIUM** | 涉及配置变更 | 预览后执行 |
| **HIGH** | 涉及数据源或核心逻辑 | 人工确认 |

### 9.2 沙箱策略

```python
class SandboxSecurity:
    # 危险函数黑名单
    DANGEROUS_FUNCTIONS = frozenset([
        'eval', 'exec', 'compile',   # 动态代码执行
        'open',                       # 文件操作
        'input', 'breakpoint',       # 交互/调试
        'exit', 'quit',              # 程序退出
        'import',                     # 模块导入
        'os.', 'sys.', 'subprocess', # 系统操作
    ])
    
    # 允许的操作
    ALLOWED = [
        'math', 'statistics',         # 数学库
        'pandas', 'numpy',           # 数据处理
        'datetime',                  # 时间处理
    ]
```

### 9.3 回滚机制

```python
class RollbackManager:
    def rollback(self, experience_id: str) -> bool:
        """回滚到指定经验之前的状态"""
        
        experience = self.knowledge_base.get(experience_id)
        
        if experience.action == "add_field":
            # 移除注册的 calculator
            self.unregister_calculator(experience.field_name)
            
        elif experience.action == "fix_bug":
            # 恢复原始代码
            self.restore_code(experience.original_code)
        
        return True
```

---

## 十、技术选型

### 10.1 LLM Provider

| Provider | 优点 | 缺点 |
|----------|------|------|
| **OpenAI (GPT-4)** | 能力强，生态成熟 | 成本高，隐私问题 |
| **Claude** | 安全，强推理能力 | 国内访问不便 |
| **本地模型** | 隐私，低成本 | 能力有限 |

**建议**: 初期使用 OpenAI，后续可扩展

### 10.2 知识库存储

| 方案 | 适用场景 |
|------|---------|
| **SQLite** | 单机，简单部署 |
| **PostgreSQL** | 多机，需要向量检索 |
| **ChromaDB** | 向量检索优先 |

**建议**: 初期 SQLite，后续可迁移

---

## 十一、监控与可观测性

### 11.1 关键指标

```python
METRICS = {
    # 进化频率
    "evolution.triggered": "counter",      # 触发进化次数
    "evolution.success": "counter",         # 成功进化次数
    "evolution.failed": "counter",          # 失败进化次数
    "evolution.rolled_back": "counter",     # 回滚次数
    
    # 字段补全
    "field.auto_added": "counter",          # 自动添加的字段数
    "field.auto_added.success_rate": "gauge", # 成功率
    
    # 性能
    "evolution.latency": "histogram",        # 进化耗时
    "llm.latency": "histogram",             # LLM 调用耗时
}
```

### 11.2 日志事件

```python
LOG_EVENTS = [
    "evolution.triggered",
    "evolution.decision_made",
    "evolution.solution_generated",
    "evolution.verified",
    "evolution.applied",
    "evolution.failed",
    "evolution.rolled_back",
]
```

---

## 十二、文档与约定

### 12.1 文件结构

```
acorn-core/src/acorn_core/
├── __init__.py
├── kernel.py
├── types.py
├── specs.py
├── services/                    # 内置服务（不是插件）
│   ├── __init__.py
│   ├── sandbox/
│   │   ├── __init__.py
│   │   └── executor.py
│   └── evolution/               # 进化系统
│       ├── __init__.py
│       ├── agent.py            # 进化代理
│       ├── context.py          # 上下文
│       ├── decision.py         # 决策
│       ├── knowledge.py        # 知识库
│       ├── handlers/           # 事件处理器
│       │   ├── __init__.py
│       │   └── field_missing.py
│       └── prompts/            # 提示词模板
│           ├── __init__.py
│           └── field_analyzer.py
└── plugins/                    # 真正的插件
    └── evo_manager.py          # (已废弃，待删除)
```

### 12.2 命名约定

| 类型 | 约定 | 示例 |
|------|------|------|
| 模块 | `snake_case` | `evolution_agent` |
| 类 | `PascalCase` | `EvolutionAgent` |
| 函数 | `snake_case` | `build_context` |
| 常量 | `SCREAMING_SNAKE` | `DANGEROUS_FUNCTIONS` |
| 命令 | `kebab-case` | `acorn evolution history` |

---

## 附录 A: 参考资料

- [pluggy 文档](https://pluggy.readthedocs.io/)
- [LLM Agent 设计模式](https://arxiv.org/abs/2308.03688)
- [Self-Healing Systems](https://research.google.com/pubs/pub42524.html)

---

## 附录 B: 变更历史

| 版本 | 日期 | 修改内容 |
|------|------|---------|
| v0.1.0 | 2026-03-23 | 初始版本 |
