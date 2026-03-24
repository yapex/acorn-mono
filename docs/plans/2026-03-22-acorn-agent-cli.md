# Acorn Agent CLI 规划

## 概述

为 acorn-agent 添加 client CLI，复用 vi-cli 的设计模式。

## 命令设计

```
# 启动 server（默认行为，无子命令时自动启动）
acorn-agent

# Client 模式（有子命令时）
acorn-agent query <symbol> [-r <fields>] [-y <years>] [-c <calculators>] [--format <format>]
acorn-agent list-fields [--source <source>] [--prefix <prefix>]
acorn-agent list-calculators
acorn-agent call <command> --args '<json>'  # 底层调试
```

## 子命令详情

### `query` - 查询财务数据

```bash
acorn-agent query <symbol> [-r <fields>] [-y <years>] [-c <calculators>] [--format <format>]

# 示例
acorn-agent query AAPL -r market_cap,operating_cash_flow -y 10
acorn-agent query 00700 -r all -c implied_growth --wacc 0.08
acorn-agent query 600519 --format json
```

选项：
- `-r, --fields`: 字段列表，逗号分隔，默认 `all`
- `-y, --years`: 年数，默认 10
- `-c, --calculators`: 计算器列表
- `--wacc`: DCF 折现率，默认 0.08
- `--g-terminal`: 永续增长率，默认 0.03
- `--format`: 输出格式 `table` | `json`，默认 `table`

### `list-fields` - 列出可用字段

```bash
acorn-agent list-fields [--source <source>] [--prefix <prefix>]
```

### `list-calculators` - 列出可用计算器

```bash
acorn-agent list-calculators
```

### `call` - 底层 HTTP 调用（调试用）

```bash
acorn-agent call vi_query --args '{"symbol": "AAPL", "fields": "market_cap"}'
```

## 技术架构

### Server: FastAPI

使用 FastAPI 实现 HTTP REST API：

```python
# server.py
from fastapi import FastAPI
import uvicorn

app = FastAPI(title="Acorn Agent", version="0.1.0")

@app.get("/health")
def health_check():
    return {"healthy": True, "version": "0.1.0"}

@app.get("/status")
def get_status():
    ...

@app.post("/execute")
def execute(command: str, args: dict):
    ...
```

启动命令：
```bash
uvicorn acorn_cli.server:app --host 0.0.0.0 --port 8000
```

### Client: httpx

使用 httpx 实现 HTTP 客户端：

```python
# client.py
import httpx

class AcornClient:
    def __init__(self, base_url: str = "http://127.0.0.1:8000"):
        self.base_url = base_url
        self._client = httpx.Client(timeout=30.0)
    
    def health_check(self) -> dict:
        return self._client.get(f"{self.base_url}/health").json()
    
    def execute(self, command: str, args: dict) -> dict:
        return self._client.post(
            f"{self.base_url}/execute",
            json={"command": command, "args": args}
        ).json()
```

### API 端点

| 端点 | 方法 | 用途 |
|------|------|------|
| `/health` | GET | 健康检查 |
| `/status` | GET | 获取系统状态 |
| `/commands` | GET | 列出可用命令 |
| `/execute` | POST | 执行命令 |

## 实现要点

1. **复用 vi-cli 代码**
   - 输出格式化逻辑 `_format_output`, `_format_value`
   - typer 框架

2. **client 调用方式**
   - 通过 `AcornClient` 调用 HTTP API
   - 检测 server 是否运行，自动启动

3. **server 启动逻辑**
   - 无子命令时启动 server（兼容现有行为）

## 文件改动

```
acorn-cli/
├── src/acorn_cli/
│   ├── server.py      # FastAPI 服务器
│   ├── client.py     # HTTP 客户端
│   ├── cli.py        # typer CLI（更新）
│   └── formatter.py  # 输出格式化（从 vi-cli 复用）
└── pyproject.toml   # 添加 fastapi, uvicorn, httpx 依赖
```

## 依赖

```toml
[project.dependencies]
fastapi = ">=0.100.0"
uvicorn = {extras = ["standard"], version = ">=0.23.0"}
httpx = ">=0.25.0"
typer = ">=0.15.0"
tabulate = ">=0.9.0"
```

## 任务清单

- [x] 创建 `server.py`（FastAPI 实现）
- [x] 创建 `client.py`（httpx 实现）
- [x] 更新 `cli.py`（使用 HTTP 客户端）
- [x] 更新 `pyproject.toml`（添加依赖）
- [ ] 测试各子命令
- [ ] 添加 `/docs` Swagger UI 文档

## 优势对比

| 特性 | 旧方案 (Unix Socket) | 新方案 (FastAPI) |
|------|---------------------|-------------------|
| 协议 | Unix Domain Socket | HTTP/1.1 |
| 服务发现 | 手动检查 socket 文件 | HTTP 请求 |
| 并发支持 | 需线程池 | 原生异步支持 |
| 文档 | 无 | 自动 Swagger UI |
| 调试 | tcpdump/socat | curl 即可 |
| 跨语言 | 困难 | 容易 |
