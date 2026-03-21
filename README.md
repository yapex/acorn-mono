# Acorn 🌰

自进化插件系统。基于 pluggy 构建的轻量级插件框架，支持自我进化。

## 项目结构

```
acorn-mono/                      # Monorepo 工作空间
├── acorn-core/                  # 核心包
│   ├── src/acorn_core/
│   │   ├── kernel.py            # 插件管理与命令路由
│   │   ├── specs.py             # 插件接口定义
│   │   ├── types.py             # Task, Response 类型
│   │   ├── models.py            # TaskContext 模型
│   │   ├── plugins/             # 内置插件
│   │   │   ├── sandbox.py       # 沙箱隔离 (Namespace/Subprocess)
│   │   │   └── evo_manager.py    # 进化管理器
│   │   └── __init__.py          # 导出核心 API
│   └── tests/                   # 测试
├── acorn-agent/                 # 持久化 Agent 服务
│   ├── src/acorn_agent/
│   │   ├── cli.py               # CLI 入口
│   │   ├── server.py            # Unix Socket 服务端
│   │   └── client.py            # 客户端 SDK
│   └── README.md                # Agent 使用文档
├── examples-plugin/          # 示例插件
├── pyproject.toml               # 工作空间配置
├── start-agent.sh               # 启动 Agent
└── stop-agent.sh                # 停止 Agent
```

## 快速开始

### 1. 安装依赖

```bash
# 安装核心包和 Agent
uv sync

# 或安装所有包
uv sync --all-packages
```

### 2. 启动 Agent 服务

```bash
# 前台运行
./start-agent.sh

# 或直接运行
acorn-agent
```

### 3. 使用客户端

```python
from acorn_agent import AcornClient

client = AcornClient()

# 方式 1: execute
result = client.execute("echo", {"message": "hello"})

# 方式 2: 快捷调用
result = client("echo", message="hello")

print(result)  # {"success": true, "data": "hello"}
```

### 4. 停止服务

```bash
./stop-agent.sh
# 或
pkill acorn-agent
```

## 开发插件

### 1. 创建项目

```bash
mkdir my-plugin && cd my-plugin
uv init -p pyproject.toml
```

### 2. pyproject.toml

```toml
[project]
name = "my-acorn-plugin"
version = "0.1.0"
requires-python = ">=3.12"

[project.entry-points."yapex.acorn.plugins"]
my_plugin = "my_plugin:plugin"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/my_plugin"]
```

### 3. 目录结构

```
my-plugin/
├── pyproject.toml
└── src/
    └── my_plugin/
        └── __init__.py
```

### 4. 实现插件

```python
# src/my_plugin/__init__.py
from acorn_core.specs import hookimpl

class MyPlugin:
    @property
    def commands(self) -> list[str]:
        return ["my_command"]
    
    @hookimpl
    def get_capabilities(self) -> dict:
        return {"commands": ["my_command"], "args": {}}
    
    @hookimpl
    def handle(self, task) -> dict:
        return {"success": True, "data": "done"}

plugin = MyPlugin()
```

### 5. 安装与测试

```bash
# 安装插件
uv pip install -e .

# 测试
cd acorn-core && uv run pytest tests/ -q
```

## 插件接口

实现以下任一方式即可被识别：

| 方法 | 说明 |
|------|------|
| `commands` (property) | 返回命令列表，如 `["echo"]` |
| `handle(task)` | 处理任务，返回 `{"success": True, "data": ...}` 或错误 |

可选：`get_capabilities()`, `on_load()`, `on_unload()`

## API

### Acorn Core

```python
from acorn_core import Acorn, Task, Response

acorn = Acorn()
acorn.load_plugins()              # 加载所有已安装插件
acorn.execute(task)               # 执行单个任务
acorn.execute_batch([task, ...])   # 批量执行
acorn.list_plugins()              # 列出已加载插件
acorn.list_capabilities()          # 列出所有能力
```

### Acorn Agent (客户端)

```python
from acorn_agent import AcornClient

client = AcornClient()

# 执行命令
result = client.execute("echo", {"message": "hello"})

# 快捷调用
result = client("echo", message="hello")
```

## Task & Response

```python
from acorn_core import Task, Response

task = Task(
    command="my_command",
    args={"key": "value"},
)

response = acorn.execute(task)
# response.success  - bool
# response.data     - 成功时数据
# response.error    - 失败时错误信息
```

## 沙箱隔离

acorn-core 内置沙箱功能，支持不同隔离级别：

```python
from acorn_core import get_default_sbox
from acorn_core.plugins.sandbox import NamespaceSandbox, SubprocessSandbox

# 默认沙箱 (NamespaceSandbox)
sandbox = get_default_sandbox()

# 进程级隔离
sandbox = SubprocessSandbox()
```

## 测试

```bash
cd acorn-core
uv run pytest tests/ -q
```

## 调试

查看已加载插件：

```python
for name, _ in acorn.list_plugins():
    print(name)
```

内置插件：`acorn_core.plugins.evo_manager` 提供 `capabilities`, `error_log` 命令。
