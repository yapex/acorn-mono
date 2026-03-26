# Evolution Brain MVP 设计文档

> **版本**: v0.1.0  
> **日期**: 2026-03-26  
> **状态**: 设计中  
> **目标**: 定义 Evolution Brain 的最小可行产品 (MVP)

---

## 核心理念

### "大脑 + 手脚" 比喻

**Evolution Brain** 是一个刚出生的 AI，它：
- ❌ 不知道什么是"财务指标"
- ❌ 不知道什么是"计算器"
- ❌ 不知道什么是"字段映射"
- ✅ 但会**学习**：从示例中发现模式
- ✅ 会**生成**：按规范产出代码
- ✅ 会**验证**：用测试用例检验
- ✅ 会**注册**：将能力接入系统

**教学类比**：
```
你教小孩做加法：
  "1+2=3，5+3=8，你来试试 2+3=?"
  小孩发现模式（相加）→ 回答 5 → 验证正确 → 学会了

Evolution Brain 同理：
  示例 [{a:1,b:2}->3, {a:5,b:3}->8] → 生成代码 → 测试通过 → 注册成功
```

---

## 架构设计

### 三层架构

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Brain Core (我们的)                             │
│                              编排教学流程                                     │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                     EvolutionBrain                                  │   │
│  │                                                                     │   │
│  │  learn_and_create(request)                                          │   │
│  │    ├── learn_pattern()     → 理解示例中的模式                       │   │
│  │    ├── generate_code()     → 按模板生成代码                         │   │
│  │    ├── validate_code()     → 用测试用例验证                         │   │
│  │    └── register_capability() → 注册到系统                           │   │
│  │                                                                     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ 调用
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              AnyTool Layer (底层能力)                        │
│                              提供 LLM、沙箱、工具编排                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐      │
│  │   LLMClient │  │   Sandbox   │  │  Grounding  │  │  Registry   │      │
│  │             │  │   (Shell)   │  │   Client    │  │             │      │
│  │  • 生成代码  │  │  • 执行代码  │  │  • 工具发现  │  │ • 注册能力   │      │
│  │  • 理解模式  │  │  • 验证结果  │  │  • 工具调用  │  │ • 持久化    │      │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘      │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ 封装
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Backend Layer (具体实现)                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                        │
│  │  DashScope  │  │  subprocess │  │   File/DB   │                        │
│  │  (Kimi)     │  │  (沙箱)      │  │  (持久化)    │                        │
│  └─────────────┘  └─────────────┘  └─────────────┘                        │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 关键原则

| 原则 | 说明 |
|------|------|
 **Brain 不直接操作 Backend** | 通过 AnyTool 接口调用，不直接访问 LLM API 或 subprocess |
| **AnyTool 是可替换的** | 可以换成其他工具编排框架，Brain 代码不变 |
| **Backend 是可替换的** | LLM 可以是 Kimi/Claude/GPT，Sandbox 可以是 Docker/E2B |
| **教学请求是唯一的输入** | Brain 只认 `TeachingRequest`，不认业务类型 |

---

## 核心数据结构

### TeachingRequest（教学请求）

```python
@dataclass
class TeachingRequest:
    """
    教 Brain 一个新能力的完整请求
    
    类比：你给小孩的教学材料
    - instruction: 课本上的说明文字
    - examples: 例题和答案
    - validation: 课后练习题
    - code_template: 填空题的模板
    - register_to: 学会后去哪里登记
    """
    
    instruction: str
    """教学说明，如：创建加法计算器"""
    
    examples: List[Dict[str, Any]]
    """学习示例，如：[{input: {a:1,b:2}, output: 3}]"""
    
    validation: Dict[str, Any]
    """验证规范，包含 test_cases 和 expected"""
    
    code_template: str
    """代码模板，Brain 填充核心逻辑"""
    
    register_to: str
    """注册目标，如 calculator_engine / field_mapping"""
```

### BrainResult（执行结果）

```python
@dataclass
class BrainResult:
    """Brain 执行教学任务的结果"""
    
    success: bool
    """是否成功完成教学"""
    
    code: Optional[str]
    """生成的代码（成功或失败都有）"""
    
    test_passed: int
    """通过的测试数"""
    
    test_total: int
    """总测试数"""
    
    error: Optional[str]
    """错误信息（失败时）"""
```

---

## 核心流程

```
用户发起教学请求
        │
        ▼
┌─────────────────┐
│  1. 学习模式    │  ← 调用 AnyTool.LLMClient
│                 │
│  从 examples 中 │
│  发现 underlying│
│  pattern        │
└────────┬────────┘
         │ pattern: "两个数相加"
         ▼
┌─────────────────┐
│  2. 生成代码    │  ← 调用 AnyTool.LLMClient
│                 │
│  用 pattern 填充 │
│  code_template  │
│  的 TODO 部分   │
└────────┬────────┘
         │ code: "result = a + b"
         ▼
┌─────────────────┐
│  3. 验证代码    │  ← 调用 AnyTool.Sandbox
│                 │
│  用 test_cases  │
│  执行代码       │
│  对比 expected  │
└────────┬────────┘
         │ passed: 3/3
         ▼
┌─────────────────┐
│  4. 注册能力    │  ← 调用 AnyTool.GroundingClient
│                 │
│  调用 register_to│
│  指定的钩子      │
└────────┬────────┘
         │ success: True
         ▼
    教学完成！
```

---

## MVP 功能范围

### ✅ 包含在 MVP 中

| 功能 | 说明 | 优先级 |
|------|------|--------|
| **基础教学** | 从示例中学习简单模式（加减乘除） | P0 |
| **代码生成** | 按模板填充核心逻辑 | P0 |
| **沙箱验证** | 执行代码并对比结果 | P0 |
| **能力注册** | 注册到 Calculator/Field 系统 | P0 |
| **错误处理** | 验证失败时返回错误信息 | P0 |

### ❌ 不包含在 MVP 中

| 功能 | 说明 | 后续版本 |
|------|------|---------|
| 复杂模式学习 | 多步骤逻辑、条件判断 | v0.2 |
| 自然语言理解 | 直接理解"创建 EBITDA" | v0.2 |
| 自我反思 | 失败时自动调整重试 | v0.3 |
| 版本管理 | 能力的版本控制和回滚 | v0.3 |
| 多模态 | 支持图片、PDF 等输入 | v0.4 |

---

## 使用示例

### 示例 1：教加法计算器

```python
# 创建 Brain
brain = EvolutionBrain()

# 准备教学材料
request = TeachingRequest(
    instruction="创建加法计算器",
    examples=[
        {"input": {"a": 1, "b": 2}, "output": 3},
        {"input": {"a": 5, "b": 3}, "output": 8},
    ],
    validation={
        "test_cases": [
            {"a": 2, "b": 3},
            {"a": 10, "b": 20},
        ],
        "expected": [5, 30]
    },
    code_template="""
REQUIRED_FIELDS = ["a", "b"]

def calculate(data, config):
    import pandas as pd
    a = data["a"]
    b = data["b"]
    # TODO: 实现核心逻辑
    result = ...
    return pd.Series(result)
""",
    register_to="calculator_engine"
)

# 开始教学
result = await brain.learn_and_create(request)

# 结果
assert result.success == True
assert result.test_passed == 2
assert "a + b" in result.code  # Brain 学会了加法
```

### 示例 2：教字段映射

```python
request = TeachingRequest(
    instruction="创建港股 total_shares 字段映射",
    examples=[
        {"input": "00700", "api_response": {"总股本": "96.12亿"}, "output": 96.12},
    ],
    validation={
        "test_cases": ["00700", "09988"],
        "expected": [96.12, 45.3]  # 期望的数值
    },
    code_template="""
FIELD_MAPPINGS = {
    "market": {
        # TODO: 添加字段映射
        "total_shares": "..."
    }
}
""",
    register_to="field_mapping"
)

result = await brain.learn_and_create(request)
```

---

## 与 AnyTool 的集成点

### 1. LLMClient（代码生成）

```python
from anytool.llm import LLMClient

self.llm = LLMClient(
    model="openai/kimi-k2.5",
    api_base="https://coding.dashscope.aliyuncs.com/v1"
)

# Brain 使用
response = await self.llm.complete(
    messages=[{"role": "user", "content": prompt}]
)
```

### 2. Sandbox（代码验证）

```python
from anytool.grounding.backends.shell import ShellBackend

sandbox = ShellBackend()

# Brain 使用
result = await sandbox.execute(test_script)
```

### 3. GroundingClient（能力注册）

```python
from anytool.grounding.core.grounding_client import GroundingClient

self.grounding = GroundingClient()

# Brain 注册工具
self.grounding.register_tool(
    name="vi_register_calculator",
    handler=self._register_calculator
)

# Brain 调用注册
result = await self.grounding.execute_tool(
    "vi_register_calculator",
    {"name": "add", "code": code}
)
```

---

## 业务层如何接入

业务层（如 ValueInvestmentPlugin）提供 `get_evolution_spec` hook：

```python
@hookimpl
def get_evolution_spec(capability_type, name, context):
    if capability_type == "calculator":
        return {
            "capability_type": "calculator",
            "name": name,
            "context": context,
            "spec_template": CALCULATOR_TEMPLATE,
            "validate_rules": [SandboxRule(), ExecuteRule()],
            "register_hook": "vi_register_calculator"
        }
```

Brain 接收这个 spec，按规范执行演化，不需要知道什么是 calculator。

---

## 下一步行动

1. **实现 Brain Core** (2-3 天)
   - `EvolutionBrain` 类
   - `learn_and_create` 主流程
   - 集成 AnyTool LLMClient

2. **实现验证模块** (1-2 天)
   - 集成 AnyTool Sandbox
   - 测试用例执行

3. **实现注册模块** (1-2 天)
   - 集成 AnyTool GroundingClient
   - 对接现有 Calculator/Field 系统

4. **MVP 测试** (1-2 天)
   - 教 Brain 做加法
   - 教 Brain 做 EBITDA
   - 验证端到端流程

---

## 附录：核心代码草稿

```python
# evolution_brain.py

from dataclasses import dataclass
from typing import List, Dict, Any, Optional

from anytool.llm import LLMClient
from anytool.grounding.core.grounding_client import GroundingClient
from anytool.grounding.backends.shell import ShellBackend


@dataclass
class TeachingRequest:
    instruction: str
    examples: List[Dict[str, Any]]
    validation: Dict[str, Any]
    code_template: str
    register_to: str


@dataclass
class BrainResult:
    success: bool
    code: Optional[str]
    test_passed: int
    test_total: int
    error: Optional[str] = None


class EvolutionBrain:
    """
    进化大脑 - 基于 AnyTool 构建
    
    职责：接收教学请求，完成学习-生成-验证-注册流程
    """
    
    def __init__(self):
        # 初始化 AnyTool 组件
        self.llm = LLMClient(model="openai/kimi-k2.5")
        self.sandbox = ShellBackend()
        self.grounding = GroundingClient()
    
    async def learn_and_create(self, request: TeachingRequest) -> BrainResult:
        """主流程：教学 → 生成 → 验证 → 注册"""
        
        # 1. 学习模式
        pattern = await self._learn_pattern(request)
        
        # 2. 生成代码
        code = await self._generate_code(request, pattern)
        
        # 3. 验证代码
        passed, total = await self._validate_code(request, code)
        
        if passed < total:
            return BrainResult(
                success=False,
                code=code,
                test_passed=passed,
                test_total=total,
                error=f"Validation failed: {passed}/{total}"
            )
        
        # 4. 注册能力
        success = await self._register_capability(request, code)
        
        return BrainResult(
            success=success,
            code=code,
            test_passed=passed,
            test_total=total
        )
    
    async def _learn_pattern(self, request: TeachingRequest) -> str:
        """使用 AnyTool LLM 学习模式"""
        prompt = f"""
Instruction: {request.instruction}

Examples:
{request.examples}

What is the pattern/rule learned from these examples?
"""
        response = await self.llm.complete(
            messages=[{"role": "user", "content": prompt}]
        )
        return response["content"]
    
    async def _generate_code(self, request: TeachingRequest, pattern: str) -> str:
        """使用 AnyTool LLM 生成代码"""
        prompt = f"""
Fill in the core logic of this template.

Template:
{request.code_template}

Pattern to implement: {pattern}

Output only the complete code:
"""
        response = await self.llm.complete(
            messages=[{"role": "user", "content": prompt}]
        )
        return self._extract_code(response["content"])
    
    async def _validate_code(self, request: TeachingRequest, code: str) -> tuple:
        """使用 AnyTool Sandbox 验证代码"""
        passed = 0
        total = len(request.validation["test_cases"])
        
        for i, test_case in enumerate(request.validation["test_cases"]):
            test_script = f"""
{code}
result = calculate({test_case}, {{}})
print(result)
"""
            result = await self.sandbox.execute(test_script)
            expected = request.validation["expected"][i]
            
            if self._compare_result(result, expected):
                passed += 1
        
        return passed, total
    
    async def _register_capability(self, request: TeachingRequest, code: str) -> bool:
        """使用 AnyTool Grounding 注册能力"""
        try:
            result = await self.grounding.execute_tool(
                request.register_to,
                {"code": code, "name": request.instruction}
            )
            return result.get("success", False)
        except Exception as e:
            print(f"Registration failed: {e}")
            return False
    
    def _extract_code(self, content: str) -> str:
        """从 LLM 响应中提取代码"""
        import re
        match = re.search(r'```python\n(.*?)\n```', content, re.DOTALL)
        return match.group(1) if match else content
    
    def _compare_result(self, actual: Any, expected: Any) -> bool:
        """比较结果"""
        if isinstance(actual, float) and isinstance(expected, float):
            return abs(actual - expected) < 0.001
        return actual == expected
```

---

**文档结束**

    model="openai/kimi-k2.5",
    api_base="https://coding.dashscope.aliyuncs.com/v1"
)

# Brain 使用
response = await self.llm.complete(
    messages=[{"role": "user", "content": prompt}]
)
```

### 2. Sandbox（代码验证）

```python
from anytool.grounding.backends.shell import ShellBackend

sandbox = ShellBackend()

# Brain 使用
result = await sandbox.execute(test_script)
```

### 3. GroundingClient（