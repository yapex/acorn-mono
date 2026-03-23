# Acorn CLI

Acorn 插件管理命令行工具。

## 架构

```
acorn-cli/
├── src/acorn_cli/
│   ├── cli.py         # CLI 入口 (acorn 命令)
│   ├── server.py      # Unix Socket 服务端
│   ├── client.py      # 客户端 SDK
│   ├── registry.py    # 插件注册表
│   └── tui.py         # TUI 配置界面
└── pyproject.toml
```

## 入口点

| 命令 | 模块 | 说明 |
|------|------|------|
| `acorn` | `acorn_cli.cli:main` | CLI 主命令 |

## 快速开始

### 安装

```bash
uv sync
```

### CLI 命令

```bash
# 插件管理
acorn list                        # 列出已安装插件
acorn install <package>           # 安装插件
acorn uninstall <name>            # 卸载插件

# 配置
acorn config tui                  # TUI 配置界面
acorn config enable <name>        # 启用插件
acorn config disable <name>       # 禁用插件
acorn config discover             # 发现可用插件
acorn config path                 # 显示注册表路径

# 插件命令 (由插件贡献)
acorn vi query 600519 -r roe      # VI 插件查询
acorn vi list-fields              # 列出可用字段
```

## 命令详解

### `acorn list`

列出已安装插件：

```
📋 已安装插件 (3)
────────────────────────────────────────────────────
✓ vi_core               📦 PyPI    v0.1.0
✓ provider_market_a     📁 本地    v0.1.0
✗ my_plugin             📦 PyPI    v1.0.0
────────────────────────────────────────────────────
```

### `acorn install`

注册插件到 acorn：

```bash
acorn install my-plugin
acorn install /path/to/plugin --name local-plugin
```

> **注意**: `acorn install` 只是将插件注册到 `registry.json`。实际安装请使用 uv：
> ```bash
> uv tool install -e acorn-cli --with-editable ./my-plugin
> ```

### `acorn config`

配置管理：

```bash
acorn config tui          # 交互式 TUI 界面
acorn config enable vi    # 启用插件
acorn config disable vi   # 禁用插件
acorn config toggle vi    # 切换状态
acorn config discover     # 发现未注册插件
acorn config path         # 显示注册表路径
```

## Python 客户端

```python
from acorn_cli.client import AcornClient

client = AcornClient()

# 执行命令
result = client.execute("health", {})
print(result)  # {"success": true, "data": {"status": "ok", ...}}

# 查询股票数据
result = client.execute("vi_query", {
    "symbol": "600519",
    "fields": "roe,gross_margin",
    "years": 10,
})

if result["success"]:
    data = result["data"]
    print(data["fields_fetched"])
```

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `ACORN_AGENT_SOCKET` | `~/.acorn/agent.sock` | Unix socket 路径 |

## 开发插件 CLI

插件可以通过 entry point 贡献 CLI 命令：

```toml
# pyproject.toml
[project.entry-points."acorn.cli.commands"]
my = "my_plugin.cli:app"
```

```python
# my_plugin/cli.py
import typer

app = typer.Typer(help="我的插件命令")

@app.command()
def hello(name: str):
    """打招呼"""
    typer.echo(f"Hello, {name}!")
```

安装后：

```bash
acorn my hello world
```

## 相关文档

- [主 README](../README.md)
- [acorn-core](../acorn-core/)
- [value-investment-plugin](../value-investment-plugin/)
