# AnyTool 集成指南

## 概述

本文档介绍如何在 acorn-mono 项目中集成 AnyTool，实现**内部自我演化能力**。

### 核心目标

**原始架构（外部 Agent 驱动）**：
- Acorn 系统本身无智能，完全依赖外部 LLM Agent 决策
- 系统没有"求生欲"，无法自我发现能力缺失并自动修复

**新目标（内部自我演化）**：
- 系统内置智能编排能力（依托 AnyTool）
- 自动检测能力缺失 → 生成扩展代码 → 验证注册
- 形成**演化闭环**，不依赖外部 Agent

```
┌─────────────────────────────────────────┐
│           用户 / 简单接口                 │
│    "分析茅台的财务状况"                    │
└─────────────────┬───────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────┐
│         Acorn 系统 (内置智能)             │
│                                         │
│  ┌─────────────────────────────────┐   │
│  │  意图理解层 (AnyTool)            │   │
│  │  • 自然语言 → 工具选择            │   │
│  │  • 任务分解与编排                 │   │
│  └─────────────────────────────────┘   │
│                                         │
│  ┌─────────────────────────────────┐   │
│  │  自我演化层 (核心)               │   │
│  │  • 检测能力缺失                  │   │
│  │  • 自动生成扩展代码              │   │
│  │  • 沙箱验证与注册                │   │
│  └─────────────────────────────────┘   │
│                                         │
│  ┌─────────────────────────────────┐   │
│  │  执行层 (Provider/Calculator)   │   │
│  │  • 数据查询                      │   │
│  │  • 计算分析                      │   │
│  └─────────────────────────────────┘   │
│                                         │
└─────────────────────────────────────────┘
```

---

## AnyTool 简介

**AnyTool** 是 HKUDS 开发的通用工具使用层 (Universal Tool-Use Layer)，为 AI Agent 提供：

- **自然语言理解**: 将用户意图转换为工具调用
- **智能工具检索**: Smart Tool RAG 自动选择最佳工具
- **多后端支持**: MCP、Shell、GUI、Web 四大后端
- **自进化质量追踪**: ToolQualityManager 持续优化工具选择

**GitHub**: https://github.com/HKUDS/AnyTool

### FastAgent 参考经验

[FastAgent](https://github.com/HKUDS/FastAgent) 是基于 AnyTool 构建的多 Agent 框架，其核心架构：

```
FastAgent (多 Agent 协调层)
    ├── HostAgent      → 高层规划、任务分解
    ├── GroundingAgent → 工具执行（继承 AnyTool）
    ├── EvalAgent      → 质量评估
    └── AgentCoordinator → 共享资源管理
```

**FastAgent 的关键创新**：
1. **Kanban 任务协调**: TODO → IN_PROGRESS → DONE/BLOCKED 状态流转
2. **事件驱动工作流**: 轮询任务状态，自动触发下一步
3. **选择性评估**: 不是每步都验证，关键步骤重点验证
4. **内容分级**: RAW → SUMMARY → KEYPOINT 自动压缩

**我们的简化策略**：
- 不需要完整的多 Agent 架构
- 不需要复杂的 Kanban 系统
- 只需要：**任务分解 → 执行 → 评估** 的简化流程

---

## 架构设计

### 简化版自我演化架构

```
┌─────────────────────────────────────────┐
│         用户 / 自然语言接口               │
│    "分析茅台未来3年的投资价值"            │
└─────────────────┬───────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────┐
│         TaskPlanner (任务规划)           │
│  • 意图理解 (LLM)                        │
│  • 分解为子任务列表:                      │
│    [查询ROE] → [计算ROIC] → [生成报告]   │
│  • 工具选择 (Smart Tool RAG)             │
└─────────────────┬───────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────┐
│         TaskExecutor (任务执行)          │
│  • 顺序执行子任务                        │
│  • 调用 vi_query / vi_calculators        │
│  • 收集执行结果                          │
└─────────────────┬───────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────┐
│         Evaluator (结果评估)             │
│  • 数据完整性检查                        │
│  • 失败 → 触发演化流程                   │
│  • 成功 → 返回最终结果                   │
└─────────────────┬───────────────────────┘
                  │
    ┌─────────────┴───────────────┐
    │                             │
    ▼                             ▼
┌─────────────┐          ┌─────────────────┐
│  返回结果    │          │  EvolutionLoop  │
│             │          │  (演化闭环)      │
└─────────────┘          │                 │
                         │ 1. 检测缺失字段  │
                         │ 2. LLM生成代码   │
                         │ 3. 沙箱验证      │
                         │ 4. 自动注册      │
                         │ 5. 重试执行      │
                         └─────────────────┘
```

### 演化闭环 (Evolution Loop)

```
┌─────────────────────────────────────────┐
│           演化闭环详细流程                │
│                                         │
│  1. 检测缺失 ◄─────────────────────┐   │
│     • 查询失败 / 字段不存在           │   │
│     • 发布 EVO_CAPABILITY_MISSING    │   │
│                              │       │   │
│  2. 生成扩展方案 ◄────────────┘       │   │
│     • LLM 生成字段映射代码             │   │
│     • 或生成 Calculator 代码          │   │
│                              │         │
│  3. 验证与注册 ─────────────►          │
│     • 沙箱验证代码正确性               │   │
│     • 自动注册到系统                   │   │
│     • 更新质量评分                     │   │
│                              │         │
│  └──────────────────────────┘         │
│           (循环往复)                    │
└─────────────────────────────────────────┘
```

---

## 安装配置

### 1. 添加依赖

在 `acorn-mono/pyproject.toml` 中添加 AnyTool 依赖：

```toml
[project]
dependencies = [
    # 现有依赖...
    "acorn-core",
    "acorn-cli",
    "vi-core",
    # ...
    
    # 添加 AnyTool
    "anytool",
]

[tool.uv.sources]
# 方式 1: 使用 Git 仓库（推荐）
anytool = { git = "https://github.com/HKUDS/AnyTool.git" }

# 方式 2: 使用本地路径（开发调试）
# anytool = { path = "../AnyTool" }
```

更新依赖：

```bash
uv sync
```

---

### 2. 配置环境变量

创建 `.env` 文件：

```bash
# DashScope Kimi K2.5 配置
OPENAI_API_KEY=sk-sp-714e7a396acd45eb9e4b67afc7696ec0

# 或 Anthropic Claude
# ANTHROPIC_API_KEY=your_key
```

---

### 3. 配置 AnyTool

创建 `anytool/config/config_grounding.json`：

```json
{
  "enabled_backends": ["system", "mcp"],
  "tool_search": {
    "search_mode": "hybrid",
    "max_tools": 40,
    "enable_llm_filter": true,
    "enable_cache_persistence": true
  },
  "tool_quality": {
    "enabled": true,
    "enable_persistence": true,
    "auto_evaluate_descriptions": true
  }
}
```

---

## 核心实现

### 1. 简化任务流程 (TaskPlanner + TaskExecutor + Evaluator)

```python
# acorn_core/evolution/task_flow.py
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from anytool import AnyTool, AnyToolConfig
from anytool.grounding.core.grounding_client import GroundingClient


@dataclass
class SubTask:
    """子任务定义"""
    task_id: str
    description: str
    tool_name: str  # 如 "vi_query", "calculator"
    parameters: Dict[str, Any]
    status: str = "pending"  # pending, running, success, failed
    result: Any = None
    error: Optional[str] = None


class TaskPlanner:
    """任务规划器 - 将自然语言分解为子任务"""
    
    def __init__(self, llm_client):
        self.llm = llm_client
        self.system_prompt = """你是一个财务分析任务规划器。
将用户的自然语言请求分解为可执行的子任务列表。

可用工具：
- vi_query: 查询财务数据，参数: symbol, items, years
- calculator: 执行计算，参数: name, inputs

输出格式（JSON）：
{
    "subtasks": [
        {"description": "...", "tool": "vi_query", "params": {...}},
        {"description": "...", "tool": "calculator", "params": {...}}
    ]
}"""
    
    async def plan(self, user_request: str) -> List[SubTask]:
        """将用户请求分解为子任务"""
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_request}
        ]
        
        response = await self.llm.complete(messages=messages)
        plan = json.loads(response["content"])
        
        subtasks = []
        for i, task in enumerate(plan["subtasks"]):
            subtasks.append(SubTask(
                task_id=f"task_{i}",
                description=task["description"],
                tool_name=task["tool"],
                parameters=task["params"]
            ))
        
        return subtasks


class TaskExecutor:
    """任务执行器 - 顺序执行子任务"""
    
    def __init__(self, grounding_client: GroundingClient):
        self.grounding = grounding_client
    
    async def execute(self, subtasks: List[SubTask]) -> List[SubTask]:
        """顺序执行所有子任务"""
        for task in subtasks:
            task.status = "running"
            
            try:
                # 通过 GroundingClient 调用工具
                result = await self.grounding.execute_task(
                    tool_name=task.tool_name,
                    parameters=task.parameters
                )
                task.result = result
                task.status = "success"
                
            except Exception as e:
                task.status = "failed"
                task.error = str(e)
                # 不中断，继续执行后续任务
        
        return subtasks


class Evaluator:
    """结果评估器 - 检查执行结果并决定是否触发演化"""
    
    def __init__(self, event_bus):
        self.event_bus = event_bus
    
    def evaluate(self, subtasks: List[SubTask]) -> Dict[str, Any]:
        """评估执行结果"""
        failed_tasks = [t for t in subtasks if t.status == "failed"]
        
        if not failed_tasks:
            return {
                "success": True,
                "result": self._aggregate_results(subtasks)
            }
        
        # 有失败任务，分析原因
        for task in failed_tasks:
            if "字段不存在" in task.error or "calculator not found" in task.error:
                # 触发演化
                self._trigger_evolution(task)
        
        return {
            "success": False,
            "failed_tasks": failed_tasks,
            "evolution_triggered": True
        }
    
    def _trigger_evolution(self, task: SubTask):
        """触发演化流程"""
        from acorn_events import AcornEvents
        
        self.event_bus.publish(
            AcornEvents.EVO_CAPABILITY_MISSING,
            capability_type="field" if task.tool_name == "vi_query" else "calculator",
            name=task.parameters.get("items") or task.parameters.get("name"),
            context={"task": task.to_dict()}
        )
    
    def _aggregate_results(self, subtasks: List[SubTask]) -> Dict:
        """聚合所有子任务结果"""
        results = {}
        for task in subtasks:
            if task.status == "success":
                results[task.task_id] = task.result
        return results


class SimpleTaskFlow:
    """简化任务流程 - 组合 Planner + Executor + Evaluator"""
    
    def __init__(self, llm_client, grounding_client, event_bus):
        self.planner = TaskPlanner(llm_client)
        self.executor = TaskExecutor(grounding_client)
        self.evaluator = Evaluator(event_bus)
    
    async def run(self, user_request: str) -> Dict[str, Any]:
        """运行完整任务流程"""
        # 1. 规划
        subtasks = await self.planner.plan(user_request)
        
        # 2. 执行
        executed_tasks = await self.executor.execute(subtasks)
        
        # 3. 评估
        result = self.evaluator.evaluate(executed_tasks)
        
        return result
```

---

### 2. 演化闭环实现

```python
# acorn_core/evolution/evolution_loop.py
from typing import Optional
import json


class EvolutionLoop:
    """
    演化闭环 - 自动扩展系统能力
    
    流程: 检测缺失 → 生成代码 → 沙箱验证 → 自动注册 → 重试
    """
    
    def __init__(self, llm_client, event_bus, plugin_manager):
        self.llm = llm_client
        self.event_bus = event_bus
        self.pm = plugin_manager
        
        # 订阅能力缺失事件
        self.event_bus.on("evo.capability.missing")(self._on_capability_missing)
    
    async def _on_capability_missing(self, event_type, sender, **kwargs):
        """处理能力缺失事件"""
        capability_type = kwargs.get("capability_type")
        name = kwargs.get("name")
        context = kwargs.get("context", {})
        
        print(f"[Evolution] 检测到能力缺失: {capability_type}/{name}")
        
        # 1. 生成扩展代码
        code = await self._generate_extension(capability_type, name, context)
        
        # 2. 沙箱验证
        if await self._validate_in_sandbox(code, capability_type):
            # 3. 自动注册
            await self._register_extension(code, capability_type, name)
            print(f"[Evolution] 成功注册新能力: {name}")
        else:
            print(f"[Evolution] 验证失败，需要人工介入")
    
    async def _generate_extension(
        self, 
        capability_type: str, 
        name: str, 
        context: dict
    ) -> str:
        """使用 LLM 生成扩展代码"""
        
        if capability_type == "field":
            prompt = self._field_extension_prompt(name, context)
        elif capability_type == "calculator":
            prompt = self._calculator_extension_prompt(name, context)
        else:
            raise ValueError(f"未知能力类型: {capability_type}")
        
        response = await self.llm.complete(
            messages=[{"role": "user", "content": prompt}]
        )
        
        # 提取代码块
        content = response["content"]
        code = self._extract_code_block(content)
        return code
    
    def _field_extension_prompt(self, field_name: str, context: dict) -> str:
        """字段扩展 Prompt"""
        return f"""请为财务数据系统创建一个新的字段扩展。

字段名: {field_name}
上下文: {json.dumps(context, ensure_ascii=False)}

要求：
1. 使用 AKShare 获取数据
2. 返回 pd.DataFrame，包含 fiscal_year 和 {field_name} 列
3. 处理数据缺失情况
4. 添加适当的错误处理

代码模板：
```python
import akshare as ak
import pandas as pd
from vi_fields_extension import StandardFields

def fetch_{field_name}(symbol: str, years: int = 10) -> pd.DataFrame:
    """获取 {field_name} 数据"""
    # TODO: 使用 AKShare API
    df = pd.DataFrame()
    df["fiscal_year"] = range(2024-years+1, 2025)
    df["{field_name}"] = None  # 填充数据
    return df

# 字段映射
FIELD_MAPPINGS = {{
    "{field_name}": "AKShare原始字段名"
}}
```

请提供完整的 Python 代码："""
    
    def _calculator_extension_prompt(self, calc_name: str, context: dict) -> str:
        """计算器扩展 Prompt"""
        return f"""请为财务分析系统创建一个新的计算器。

计算器名: {calc_name}
上下文: {json.dumps(context, ensure_ascii=False)}

要求：
1. 定义 REQUIRED_FIELDS
2. 实现 calculate(data, config) 函数
3. 返回 pd.Series
4. 处理除零等边界情况

代码模板：
```python
import pandas as pd

REQUIRED_FIELDS = ["field_a", "field_b"]

def calculate(data: dict, config: dict) -> pd.Series:
    """
    计算 {calc_name}
    
    Args:
        data: dict[str, pd.Series] - 输入字段数据
        config: dict - 配置参数
    
    Returns:
        pd.Series - 计算结果
    """
    # TODO: 实现计算逻辑
    result = data["field_a"] / data["field_b"]
    return result
```

请提供完整的 Python 代码："""
    
    async def _validate_in_sandbox(self, code: str, capability_type: str) -> bool:
        """在沙箱中验证代码"""
        from acorn_core.sandbox import validate_calculator_code
        
        try:
            if capability_type == "calculator":
                # 构造测试数据
                test_data = {
                    "data": {
                        "field_a": pd.Series([1.0, 2.0, 3.0]),
                        "field_b": pd.Series([2.0, 4.0, 6.0])
                    },
                    "config": {}
                }
                
                result = validate_calculator_code(code, test_data, {"pd": pd})
                return result["success"]
            
            elif capability_type == "field":
                # 执行代码检查语法
                compile(code, "<string>", "exec")
                return True
            
        except Exception as e:
            print(f"[Evolution] 验证失败: {e}")
            return False
    
    async def _register_extension(
        self, 
        code: str, 
        capability_type: str, 
        name: str
    ):
        """自动注册扩展"""
        if capability_type == "calculator":
            # 调用 vi_register_calculator
            self.pm.hook.vi_register_calculator(
                name=name,
                code=code,
                required_fields=self._extract_required_fields(code),
                description=f"Auto-generated {name}"
            )
        
        elif capability_type == "field":
            # 保存字段映射到 Provider
            self._save_field_mapping(name, code)
    
    def _extract_code_block(self, content: str) -> str:
        """从 LLM 响应中提取代码块"""
        import re
        match = re.search(r'```python\n(.*?)\n```', content, re.DOTALL)
        if match:
            return match.group(1)
        return content
    
    def _extract_required_fields(self, code: str) -> list:
        """从代码中提取 REQUIRED_FIELDS"""
        import re
        match = re.search(r'REQUIRED_FIELDS\s*=\s*(\[.*?\])', code)
        if match:
            return eval(match.group(1))
        return []
```

---

### 3. 集成到 Acorn 系统

```python
# acorn_core/kernel.py (修改)
from acorn_core.evolution import SimpleTaskFlow, EvolutionLoop

class AcornKernel:
    def __init__(self):
        # 现有初始化...
        self.pm = PluginManager("acorn")
        self.event_bus = EventBus()
        
        # 新增: AnyTool 集成
        self._init_anytool_integration()
    
    def _init_anytool_integration(self):
        """初始化 AnyTool 集成"""
        from anytool import AnyTool, AnyToolConfig
        from anytool.llm import LLMClient
        from anytool.grounding.core.grounding_client import GroundingClient
        
        # 1. 创建 LLMClient
        llm_client = LLMClient(
            model="openai/kimi-k2.5",
            api_base="https://coding.dashscope.aliyuncs.com/v1"
        )
        
        # 2. 创建 GroundingClient
        grounding_client = GroundingClient()
        
        # 3. 注册 Acorn 工具到 GroundingClient
        self._register_acorn_tools(grounding_client)
        
        # 4. 创建简化任务流程
        self.task_flow = SimpleTaskFlow(
            llm_client=llm_client,
            grounding_client=grounding_client,
            event_bus=self.event_bus
        )
        
        # 5. 创建演化闭环
        self.evolution_loop = EvolutionLoop(
            llm_client=llm_client,
            event_bus=self.event_bus,
            plugin_manager=self.pm
        )
    
    def _register_acorn_tools(self, grounding_client):
        """将 Acorn 工具注册到 GroundingClient"""
        # 注册 vi_query 工具
        grounding_client.register_tool(
            name="vi_query",
            description="查询股票财务数据",
            parameters={
                "symbol": {"type": "string", "description": "股票代码"},
                "items": {"type": "string", "description": "查询字段"},
                "years": {"type": "integer", "description": "年数"}
            },
            handler=self._handle_vi_query
        )
        
        # 注册 calculator 工具
        grounding_client.register_tool(
            name="calculator",
            description="执行财务计算",
            parameters={
                "name": {"type": "string", "description": "计算器名称"},
                "inputs": {"type": "object", "description": "输入数据"}
            },
            handler=self._handle_calculator
        )
    
    async def handle_natural_language_request(self, request: str) -> dict:
        """处理自然语言请求"""
        return await self.task_flow.run(request)
```

---

## 使用示例

### 示例 1: 自然语言查询

```python
import asyncio
from acorn_core.kernel import AcornKernel

async def main():
    kernel = AcornKernel()
    
    # 自然语言请求
    result = await kernel.handle_natural_language_request(
        "分析贵州茅台(600519)的盈利能力趋势"
    )
    
    if result["success"]:
        print("分析结果:", result["result"])
    else:
        if result.get("evolution_triggered"):
            print("系统正在自动扩展能力，请稍后重试...")

asyncio.run(main())
```

### 示例 2: CLI 命令

```bash
# 自然语言查询
acorn analyze "茅台和五粮液的ROE对比"

# 系统输出:
# [TaskPlanner] 分解为3个子任务:
#   1. 查询茅台ROE
#   2. 查询五粮液ROE  
#   3. 生成对比报告
# [TaskExecutor] 执行任务...
# [Evolution] 检测到能力缺失: field/total_shares
# [Evolution] 成功注册新能力: total_shares
# [Evaluator] 任务完成
```

---

## 配置参考

### AnyToolConfig 完整配置

```python
from anytool import AnyToolConfig

config = AnyToolConfig(
    # LLM 配置
    llm_model="openai/kimi-k2.5",
    llm_enable_thinking=False,
    llm_timeout=120.0,
    llm_max_retries=3,
    llm_kwargs={
        "api_base": "https://coding.dashscope.aliyuncs.com/v1",
    },
    
    # 专用模型（可选）
    tool_retrieval_model=None,  # 工具检索专用模型
    visual_analysis_model=None,  # 视觉分析专用模型
    
    # Grounding 配置
    grounding_max_iterations=20,
    
    # 后端配置
    backend_scope=["system", "mcp"],  # 只启用 system 和 mcp 后端
    
    # 录制配置
    enable_recording=False,
    
    # 日志配置
    log_level="INFO",
)
```

---

## 演化流程测试

```python
# 测试演化闭环
import asyncio

async def test_evolution():
    """测试自动演化能力"""
    kernel = AcornKernel()
    
    # 查询一个当前不存在的字段
    result = await kernel.handle_natural_language_request(
        "查询腾讯(00700)的 total_shares"
    )
    
    # 预期流程:
    # 1. 检测到字段缺失
    # 2. 触发 EVO_CAPABILITY_MISSING
    # 3. LLM 生成字段映射代码
    # 4. 沙箱验证
    # 5. 自动注册到港股 Provider
    # 6. 重试查询
    
    assert result["success"] == True
    print("演化测试通过!")

asyncio.run(test_evolution())
```

---

## 相关文档

- [AnyTool GitHub](https://github.com/HKUDS/AnyTool)
- [FastAgent GitHub](https://github.com/HKUDS/FastAgent) - 参考多 Agent 架构
- [LiteLLM 文档](https://docs.litellm.ai/)
- [Acorn 自进化状态](./self_evolution_status.md)
- [Acorn 字段扩展设计](./field-extension-design.md)

---

## 更新记录

| 日期 | 版本 | 说明 |
|------|------|------|
| 2026-03-26 | 0.2.0 | 重构为内部自我演化架构，参考 FastAgent 简化实现 |
| 2026-03-26 | 0.1.0 | 初始版本，基础 AnyTool 集成 |

---

## 关键决策总结

| 决策点 | 选择 | 理由 |
|--------|------|------|
| **多 Agent 架构** | ❌ 不使用 | 过于复杂，单 Agent + 模块化即可 |
| **Kanban 系统** | ❌ 不使用 | 简化为 TaskPlanner → Executor → Evaluator |
| **AnyTool 依赖** | ✅ 使用 | 获得 Smart Tool RAG 和质量追踪 |
| **演化闭环** | ✅ 自研 | AnyTool 不提供代码生成能力 |
| **评估策略** | ✅ 选择性评估 | 参考 FastAgent，失败时触发演化 |
