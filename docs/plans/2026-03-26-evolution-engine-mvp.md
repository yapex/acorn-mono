# Evolution Engine MVP 设计

> **版本**: v0.1.0  
> **日期**: 2026-03-26  
> **核心目标**: 用 AnyTool 替代外部 Agent，自动完成演化闭环

---

## 核心流程对比

### 旧流程（依赖外部 Agent）

```
用户查询 EBITDA
    ↓
CalculatorEngine 发现缺失 → 发布 EVO_CAPABILITY_MISSING
    ↓
EvoManager 接收事件 → get_evolution_spec() 返回 Prompt
    ↓
打印到控制台 ← 停在这里！
    ↓
[等待外部 Agent 读取]
[外部 Agent 调用 LLM 生成代码]
[外部 Agent 手动注册]
[外部 Agent 重试查询]
```

### 新流程（Evolution Engine + AnyTool）

```
用户查询 EBITDA
    ↓
CalculatorEngine 发现缺失 → 发布 EVO_CAPABILITY_MISSING
    ↓
EvolutionEngine 接收事件 → get_evolution_spec() 返回 Prompt
    ↓
调用 AnyTool.execute(spec)
    ↓
AnyTool 理解 Prompt → 生成代码 → 自我验证 → 返回结果
    ↓
EvolutionEngine 注册代码 → 重试原请求
    ↓
返回 EBITDA 结果
```

**关键变化**: 用 AnyTool 替代外部 Agent，完全自动化。

---

## 架构设计

```
┌─────────────────────────────────────────────────────────────────┐
│                         业务模块（如 CalculatorEngine）          │
│                                                                 │
│  1. 发现缺失 → 发布 EVO_CAPABILITY_MISSING                      │
│  2. 提供 get_evolution_spec() → 返回 "如何创建计算器" 的 Prompt │
│                                                                 │
│  业务模块知道：                                                   │
│  - 如何定义 Calculator（REQUIRED_FIELDS, calculate 函数）       │
│  - 如何验证（测试用例）                                          │
│  - 如何注册（vi_register_calculator）                           │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼ 事件 + Prompt
┌─────────────────────────────────────────────────────────────────┐
│                      EvolutionEngine（我们实现）                 │
│                                                                 │
│  职责：接收事件 → 获取 Prompt → 调用 AnyTool → 注册结果        │
│                                                                 │
│  async def on_capability_missing(event):                        │
│      spec = plugin.get_evolution_spec(...)                      │
│      result = await anytool.execute(spec)  # AnyTool 完成一切   │
│      if result.success:                                         │
│          await register(result.code)                            │
│          await retry_original_request()                         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼ Prompt
┌─────────────────────────────────────────────────────────────────┐
│                      AnyTool（第三方 Agent）                     │
│                                                                 │
│  职责：理解 Prompt → 生成代码 → 验证 → 返回                    │
│                                                                 │
│  输入：自然语言 Prompt（包含任务、示例、验证要求）              │
│  输出：{code, test_result, success}                            │
│                                                                 │
│  AnyTool 内部：                                                  │
│  - 用 LLM 生成代码                                               │
│  - 用 Sandbox 验证                                               │
│  - 失败自动重试                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## MVP 最小实现

### 1. 业务模块提供 Prompt

```python
# CalculatorEngine.get_evolution_spec()
def get_evolution_spec(capability_type, name, context):
    if capability_type == "calculator":
        return f"""
请创建一个 Python 计算器，名称为 "{name}"。

要求：
1. 定义 REQUIRED_FIELDS = [...]
2. 实现 calculate(data, config) 函数
3. 返回 pd.Series

示例格式：
```python
REQUIRED_FIELDS = ["field_a", "field_b"]

def calculate(data, config):
    import pandas as pd
    a = data["field_a"]
    b = data["field_b"]
    result = a / b  # 你的计算逻辑
    return pd.Series(result)
```

测试要求：
- 用 data = {{"field_a": pd.Series([1,2,3]), "field_b": pd.Series([2,4,6])}} 测试
- 确保结果正确
- 处理除零等边界情况

请生成完整代码，并自我验证测试用例是否通过。
"""
```

### 2. EvolutionEngine 调用 AnyTool

```python
# evolution_engine.py
from anytool import AnyTool, AnyToolConfig

class EvolutionEngine:
    def __init__(self):
        self.anytool = AnyTool(config=AnyToolConfig(
            llm_model="openai/kimi-k2.5",
            backend_scope=["shell"],  # 使用 Sandbox
        ))
    
    async def on_capability_missing(self, event):
        """接收 EVO_CAPABILITY_MISSING 事件"""
        
        # 1. 获取业务模块提供的 Prompt
        spec = self._get_evolution_spec(
            event.capability_type,
            event.name,
            event.context
        )
        
        if not spec:
            print(f"没有插件能提供 {event.name} 的进化规范")
            return
        
        # 2. 调用 AnyTool 完成一切
        print(f"开始演化: {event.name}")
        
        result = await self.anytool.execute(
            task=spec,
            # AnyTool 自己决定如何完成：
            # - 用 LLM 生成代码
            # - 用 Sandbox 验证
            # - 失败自动重试
        )
        
        # 3. 处理结果
        if result.success:
            # 注册新能力
            await self._register(
                event.capability_type,
                event.name,
                result.code
            )
            
            # 重试原请求
            await self._retry_original_request(event)
            
            print(f"演化成功: {event.name}")
        else:
            print(f"演化失败: {event.name}, 错误: {result.error}")
```

### 3. AnyTool 完成内部流程

AnyTool 接收到 Prompt 后，自主完成：

```python
# AnyTool 内部（我们不需要实现，直接使用）
class AnyTool:
    async def execute(self, task: str):
        # 1. 理解任务（LLM）
        # 2. 生成代码（LLM）
        # 3. 验证代码（Sandbox）
        # 4. 返回结果
        
        # 伪代码：
        code = await self.llm.generate(task)
        test_result = await self.sandbox.run(code)
        
        if test_result.success:
            return {"success": True, "code": code}
        else:
            # 自动重试
            return await self._retry_with_feedback(task, test_result.error)
```

---

## MVP 测试场景

### 场景 1：翻译模块

```python
# 模拟翻译模块
class TranslatorPlugin:
    def translate(self, text: str, from_lang: str, to_lang: str):
        if not self._has_translator(from_lang, to_lang):
            # 发布缺失事件
            publish_event("EVO_CAPABILITY_MISSING",
                capability_type="translator",
                name=f"{from_lang}_to_{to_lang}",
                context={"text": text}
            )
            raise CapabilityMissing()
        
        # 正常翻译...
    
    def get_evolution_spec(self, capability_type, name, context):
        if capability_type == "translator":
            return f"""
请创建一个翻译器，将中文翻译成英文。

要求：
1. 实现 translate(text: str) -> str 函数
2. 可以调用外部 API 或自己实现
3. 确保翻译准确

测试用例：
- "你好" → "Hello"
- "谢谢" → "Thank you"

请生成代码并验证测试用例通过。
"""

# 测试
async def test_translation():
    # 第一次调用：触发演化
    result = await translator.translate("你好", "zh", "en")
    # EvolutionEngine 自动创建翻译器
    # 返回 "Hello"
    
    # 第二次调用：直接使用
    result = await translator.translate("谢谢", "zh", "en")
    # 返回 "Thank you"
```

### 场景 2：Calculator 模块（我们的真实业务）

```python
# 第一次查询 EBITDA（假设不存在）
result = await vi_query(symbol="600519", items="ebitda")
# 输出：
# [Evolution] 发现缺失: calculator/ebidta
# [Evolution] 获取规范...
# [Evolution] 调用 AnyTool...
# [Evolution] 生成代码...
# [Evolution] 验证通过
# [Evolution] 注册成功
# [Evolution] 重试查询...
# 返回：ebitda 数据

# 第二次查询 EBITDA（已存在）
result = await vi_query(symbol="600519", items="ebitda")
# 直接返回数据，无需演化
```

---

## 关键设计决策

| 决策 | 选择 | 理由 |
|------|------|------|
| Prompt 由谁提供 | 业务模块 | 业务模块知道如何定义自己的能力 |
| 代码生成由谁完成 | AnyTool | AnyTool 是 Agent，能自主完成 |
| 验证由谁完成 | AnyTool | AnyTool 内置 Sandbox |
| 注册由谁完成 | EvolutionEngine | 需要统一管理和持久化 |
| 重试由谁完成 | EvolutionEngine | 需要协调原请求重试 |

---

## 与现有系统的对比

| 组件 | 之前 | 现在 |
|------|------|------|
| EvoManager | 打印 Prompt，等待外部 Agent | 调用 AnyTool 自动完成 |
| 外部 Agent | 人工或外部 LLM | 删除，用 AnyTool 替代 |
| 代码生成 | 外部完成 | AnyTool 内部完成 |
| 验证 | 外部完成 | AnyTool 内部完成 |
| 注册 | 外部调用 | EvolutionEngine 调用 |
| 重试 | 外部触发 | EvolutionEngine 触发 |

---

## 下一步行动

1. **实现 EvolutionEngine** (1-2 天)
   - 接收 EVO_CAPABILITY_MISSING 事件
   - 调用 AnyTool.execute(spec)
   - 处理结果并注册

2. **对接现有系统** (1 天)
   - 替换 EvoManager 的打印逻辑
   - 接入 CalculatorEngine 的 get_evolution_spec

3. **MVP 测试** (1 天)
   - 测试翻译模块场景
   - 测试 Calculator 场景

---

**核心认知**: EvolutionEngine 不是"教"AnyTool 怎么做，而是"告诉"AnyTool 做什么，让 AnyTool 自己完成。
