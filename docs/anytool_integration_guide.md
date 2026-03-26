# AnyTool 集成指南

## 概述

本文档介绍如何在 acorn-mono 项目中集成 AnyTool，实现通过自然语言进行公司财务分析的能力。

---

## AnyTool 简介

**AnyTool** 是 HKUDS 开发的通用工具使用层 (Universal Tool-Use Layer)，为 AI Agent 提供：

- **自然语言理解**: 将用户意图转换为工具调用
- **智能工具检索**: Smart Tool RAG 自动选择最佳工具
- **多后端支持**: MCP、Shell、GUI、Web 四大后端
- **自进化质量追踪**: 持续优化工具选择策略

**GitHub**: https://github.com/HKUDS/AnyTool

---

## 集成方案

### 架构设计

```
┌─────────────────────────────────────────┐
│           用户 / LLM Agent               │
│    "分析贵州茅台的财务健康状况"            │
└─────────────────┬───────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────┐
│         AnyTool (自然语言层)              │
│  • 意图理解                              │
│  • 工具选择                              │
│  • 任务编排                              │
└─────────────────┬───────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────┐
│      Acorn MCP Server / Bridge          │
│  • 暴露 vi_query 为工具                  │
│  • 数据格式转换                          │
└─────────────────┬───────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────┐
│           Acorn 价值投资系统              │
│  • vi_core 查询引擎                      │
│  • provider_market_* 数据源              │
│  • vi_calculators 计算器                 │
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

# 方式 3: 使用特定分支或提交
# anytool = { git = "https://github.com/HKUDS/AnyTool.git", rev = "main" }
```

然后更新依赖：

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

# 或 OpenAI
# OPENAI_API_KEY=your_key
```

---

### 3. 配置 MCP Server（可选）

创建 `anytool/config/config_mcp.json`：

```json
{
  "mcpServers": {
    "acorn_vi": {
      "command": "python",
      "args": ["-m", "acorn_anytool_bridge.mcp_server"],
      "env": {
        "TUSHARE_TOKEN": "${TUSHARE_TOKEN}"
      }
    }
  }
}
```

---

## 使用示例

### 示例 1: 基础自然语言查询

```python
import asyncio
import os
from anytool import AnyTool, AnyToolConfig

# 设置 API Key
os.environ["OPENAI_API_KEY"] = "sk-sp-714e7a396acd45eb9e4b67afc7696ec0"

async def analyze_company():
    """自然语言分析公司财务"""
    
    config = AnyToolConfig(
        llm_model="openai/kimi-k2.5",
        llm_kwargs={
            "api_base": "https://coding.dashscope.aliyuncs.com/v1",
        },
        backend_scope=["system"],  # 简化配置
    )
    
    async with AnyTool(config=config) as tool_layer:
        result = await tool_layer.execute(
            "查询贵州茅台(600519)最近5年的ROE数据，并分析其变化趋势"
        )
        
        print(f"状态: {result['status']}")
        print(f"响应:\n{result['response']}")
        
        return result

# 运行
asyncio.run(analyze_company())
```

---

### 示例 2: 集成 Acorn 财务数据

```python
import asyncio
from anytool import AnyTool, AnyToolConfig
from acorn_cli.client import AcornClient

async def analyze_with_acorn_data():
    """结合 AnyTool 和 Acorn 进行深度分析"""
    
    # 1. 先通过 Acorn 获取数据
    acorn = AcornClient()
    financial_data = acorn.execute("vi_query", {
        "symbol": "600519",
        "items": "roe,net_profit,revenue",
        "years": 5,
    })
    
    # 2. 使用 AnyTool 进行自然语言分析
    config = AnyToolConfig(
        llm_model="openai/kimi-k2.5",
        llm_kwargs={
            "api_base": "https://coding.dashscope.aliyuncs.com/v1",
        },
    )
    
    async with AnyTool(config=config) as tool_layer:
        # 将数据作为上下文传入
        result = await tool_layer.execute(
            f"基于以下财务数据，分析贵州茅台的投资价值:\n{financial_data}",
            context={"financial_data": financial_data}
        )
        
        return result

asyncio.run(analyze_with_acorn_data())
```

---

### 示例 3: 创建 CLI 命令

在 `acorn-cli` 中添加自然语言分析命令：

```python
# acorn-cli/src/acorn_cli/commands/analyze.py
import asyncio
import typer
from anytool import AnyTool, AnyToolConfig

app = typer.Typer(help="自然语言财务分析")

@app.command()
def query(
    text: str = typer.Argument(..., help="自然语言查询"),
    model: str = typer.Option("openai/kimi-k2.5", help="LLM 模型"),
):
    """使用自然语言查询财务数据"""
    
    async def run():
        config = AnyToolConfig(
            llm_model=model,
            llm_kwargs={
                "api_base": "https://coding.dashscope.aliyuncs.com/v1",
            },
        )
        
        async with AnyTool(config=config) as tool_layer:
            result = await tool_layer.execute(text)
            print(result["response"])
    
    asyncio.run(run())

# 注册到主 CLI
# acorn-cli/src/acorn_cli/cli.py
from .commands import analyze
app.add_typer(analyze.app, name="analyze")
```

使用：

```bash
acorn analyze "贵州茅台和五粮液的ROE对比分析"
```

---

## MCP Server 桥接实现

创建 `acorn_anytool_bridge/mcp_server.py`：

```python
"""Acorn 的 AnyTool MCP Server"""
import asyncio
import json
from mcp.server import Server
from mcp.types import Tool, TextContent
from acorn_cli.client import AcornClient

app = Server("acorn-anytool")

@app.list_tools()
async def list_tools():
    """列出可用工具"""
    return [
        Tool(
            name="vi_query",
            description="查询股票财务数据，支持 ROE、净利润、营收等指标",
            inputSchema={
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "股票代码，如 600519"
                    },
                    "items": {
                        "type": "string",
                        "description": "查询项，逗号分隔，如 roe,net_profit"
                    },
                    "years": {
                        "type": "integer",
                        "description": "查询年数",
                        "default": 5
                    }
                },
                "required": ["symbol", "items"]
            }
        ),
        Tool(
            name="vi_analyze",
            description="分析公司财务状况",
            inputSchema={
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "股票代码"
                    },
                    "metrics": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "分析指标"
                    }
                },
                "required": ["symbol"]
            }
        ),
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict):
    """执行工具调用"""
    client = AcornClient()
    
    if name == "vi_query":
        result = client.execute("vi_query", {
            "symbol": arguments["symbol"],
            "items": arguments["items"],
            "years": arguments.get("years", 5),
        })
        return [TextContent(
            type="text",
            text=json.dumps(result, indent=2, ensure_ascii=False)
        )]
    
    elif name == "vi_analyze":
        # 获取数据并分析
        metrics = arguments.get("metrics", ["roe", "net_profit", "revenue"])
        result = client.execute("vi_query", {
            "symbol": arguments["symbol"],
            "items": ",".join(metrics),
            "years": 5,
        })
        return [TextContent(
            type="text",
            text=json.dumps(result, indent=2, ensure_ascii=False)
        )]
    
    else:
        return [TextContent(type="text", text=f"未知工具: {name}")]

if __name__ == "__main__":
    app.run()
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
    llm_rate_limit_delay=0.0,
    llm_kwargs={
        "api_base": "https://coding.dashscope.aliyuncs.com/v1",
    },
    
    # 专用模型（可选）
    tool_retrieval_model=None,
    visual_analysis_model=None,
    
    # Grounding 配置
    grounding_max_iterations=20,
    grounding_system_prompt=None,
    
    # 后端配置
    backend_scope=["system", "shell", "mcp", "web"],
    
    # 录制配置
    enable_recording=False,
    enable_screenshot=True,
    enable_video=True,
    
    # 日志配置
    log_level="INFO",
    log_to_file=False,
)
```

---

## 支持的 LLM 模型

AnyTool 通过 LiteLLM 支持多种模型：

| 提供商 | 模型示例 | 配置方式 |
|--------|---------|---------|
| **DashScope** | `openai/kimi-k2.5` | `api_base=https://coding.dashscope.aliyuncs.com/v1` |
| **Anthropic** | `anthropic/claude-3-sonnet` | `ANTHROPIC_API_KEY` |
| **OpenAI** | `openai/gpt-4` | `OPENAI_API_KEY` |
| **OpenRouter** | `openrouter/anthropic/claude-sonnet-4.5` | `OPENROUTER_API_KEY` |
| **Azure** | `azure/gpt-4` | `AZURE_API_KEY` + `AZURE_API_BASE` |
| **Ollama** | `ollama/llama3` | `OLLAMA_API_BASE` |

---

## 测试验证

### 测试 LiteLLM 连接

```python
import asyncio
import litellm

async def test():
    response = await litellm.acompletion(
        model="openai/kimi-k2.5",
        messages=[{"role": "user", "content": "你好"}],
        api_key="sk-sp-714e7a396acd45eb9e4b67afc7696ec0",
        api_base="https://coding.dashscope.aliyuncs.com/v1",
    )
    print(response.choices[0].message.content)

asyncio.run(test())
```

### 测试 AnyTool 完整流程

```python
import asyncio
from anytool import AnyTool, AnyToolConfig

async def test():
    config = AnyToolConfig(
        llm_model="openai/kimi-k2.5",
        llm_kwargs={
            "api_base": "https://coding.dashscope.aliyuncs.com/v1",
        },
        backend_scope=["system"],
    )
    
    async with AnyTool(config=config) as tool_layer:
        result = await tool_layer.execute("你好，请自我介绍")
        print(result["response"])

asyncio.run(test())
```

---

## 常见问题

### Q: AnyTool 是否已发布到 PyPI？

A: 尚未发布。目前需要通过 Git 依赖安装：

```toml
anytool = { git = "https://github.com/HKUDS/AnyTool.git" }
```

### Q: Kimi K2.5 是否支持工具调用？

A: 支持。通过 OpenAI 兼容模式可以正常使用。

### Q: 如何处理大财务数据的结果？

A: AnyTool 内置结果摘要功能，自动处理大文本：

```python
config = AnyToolConfig(
    llm_kwargs={
        "summarize_threshold_chars": 50000,  # 超过此阈值自动摘要
    }
)
```

### Q: 如何调试工具选择过程？

A: 启用 DEBUG 日志：

```python
config = AnyToolConfig(
    log_level="DEBUG",
    log_to_file=True,
    log_file_path="./logs/anytool_debug.log",
)
```

---

## 相关文档

- [AnyTool GitHub](https://github.com/HKUDS/AnyTool)
- [LiteLLM 文档](https://docs.litellm.ai/)
- [MCP 协议](https://modelcontextprotocol.io/)
- [Acorn CLI README](../acorn-cli/README.md)
- [Value Investment Plugin README](../value-investment/README.md)

---

## 更新记录

| 日期 | 版本 | 说明 |
|------|------|------|
| 2026-03-26 | 0.1.0 | 初始版本，集成 AnyTool 0.1.0 |

---

## 联系方式

如有问题，请联系：
- AnyTool: https://github.com/HKUDS/AnyTool/issues
- Acorn: 项目维护者