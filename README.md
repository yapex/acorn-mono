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
│   │   │   ├── sandbox.py       # 沙箱隔离
│   │   │   └── evo_manager.py   # 进化管理器
│   │   └── __init__.py          # 导出核心 API
│   └── tests/                   # 测试
├── acorn-cli/                   # CLI 工具
│   ├── src/acorn_cli/
│   │   ├── cli.py               # CLI 入口 (acorn 命令)
│   │   ├── server.py            # Unix Socket 服务端
│   │   ├── client.py            # 客户端 SDK
│   │   ├── registry.py          # 插件注册表
│   │   └── tui.py               # TUI 配置界面
│   └── README.md                # 使用文档
├── value-investment-plugin/     # 价值投资插件
├── examples-plugin/             # 示例插件
└── pyproject.toml               # 工作空间配置
```

## 快速开始

### 1. 安装依赖

```bash
# 安装核心包和 CLI
uv sync

# 或安装所有包
uv sync --all-packages
```

### 2. 使用 CLI

```bash
# 列出已安装插件
acorn list

# 配置插件（启用/禁用）
acorn config enable <plugin>
acorn config disable <plugin>

# 交互式配置
acorn config tui

# 查询股票数据 (vi 插件命令)
acorn vi query 600519 --fields roe,gross_margin --years 10

# 列出可用字段
acorn vi list-fields

# 列出可用计算器
acorn vi list-calculators
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

# 可选：贡献 CLI 命令
[project.entry-points."acorn.cli.commands"]
my = "my_plugin.cli:app"

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
        ├── __init__.py      # 插件实现
        └── cli.py           # CLI 命令 (可选)
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

### 5. 实现 CLI 命令 (可选)

```python
# src/my_plugin/cli.py
import typer

app = typer.Typer(help="我的插件命令")

@app.command()
def hello(name: str):
    """打招呼"""
    typer.echo(f"Hello, {name}!")
```

### 6. 安装与测试

```bash
# 安装插件
uv pip install -e .

# 注册到 acorn
acorn install my-acorn-plugin

# 测试
acorn my hello world
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

### Acorn CLI Client (RPC)

```python
from acorn_cli.client import AcornClient

client = AcornClient()

# 执行命令
result = client.execute("echo", {"message": "hello"})

# 查询股票数据
result = client.execute("vi_query", {
    "symbol": "600519",
    "fields": "roe,gross_margin",
    "years": 10,
})
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

## 进化模式 (Evolution)

通过命令行创建新的计算器（Calculator）。

### 基本流程

```bash
# 1. 检查计算器是否存在
acorn evolution --intent check --field-name graham_value

# 输出: not_found: graham_value
#       intent: create
#       need: --intent create ...

# 2. 创建计算器
acorn evolution \
  --intent create \
  --field-name graham_value \
  --formula "sqrt(22.5 * basic_eps * book_value_per_share)" \
  --required-fields "basic_eps,book_value_per_share,close" \
  --description "格雷厄姆估值" \
  --unit "yuan" \
  --code '<Python 代码>' \
  --confirm
```

### 计算器代码规范

```python
REQUIRED_FIELDS = ["basic_eps", "book_value_per_share", "close"]

def calculate(data, config):
    """
    格雷厄姆估值计算器
    
    Args:
        data: dict[str, pd.Series]，字段数据
        config: dict，用户配置
        
    Returns:
        pd.Series，计算结果
    """
    import pandas as pd
    
    eps = data["basic_eps"]
    bps = data["book_value_per_share"]
    close = data["close"]
    
    graham_value = (22.5 * eps * bps) ** 0.5
    margin_of_safety = (graham_value - close) / graham_value
    
    return pd.Series({
        "graham_value": graham_value,
        "current_price": close,
        "margin_of_safety": margin_of_safety,
    })
```

### 计算器加载规则

计算器文件保存在执行目录下的 `calculators/` 子目录：

| 执行目录 | calculators 位置 |
|---------|----------------|
| `acorn-mono/` | `acorn-mono/calculators/` |
| `value-investment-plugin/` | `value-investment-plugin/calculators/` |
| `/tmp` | `/tmp/calculators/` (自动创建) |

加载优先级（后者覆盖前者）：
1. `builtin` - 内置计算器 (value-investment-plugin/calculators/)
2. `cwd` - 当前工作目录下的 calculators/

### 常用字段参考

| 字段名 | 说明 |
|-------|------|
| `basic_eps` | 基本每股收益 |
| `book_value_per_share` | 每股净资产 |
| `close` | 收盘价 |
| `operating_cash_flow` | 经营现金流 |
| `market_cap` | 总市值 |
| `net_profit` | 净利润 |
| `total_equity` | 所有者权益 |
| `roe` | 净资产收益率 |
| `roa` | 资产收益率 |
| `gross_margin` | 毛利率 |
