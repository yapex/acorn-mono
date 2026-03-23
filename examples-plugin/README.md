# Examples Plugin 🌳

Acorn 官方示例插件，作为开发新插件的参考模板。

## 安装

```bash
uv pip install -e examples-plugin/
acorn install examples-plugin
```

## 命令

| 命令 | 说明 | 参数 |
|------|------|------|
| `echo` | 回显消息 | `message` (string, required) |

## 使用

### 通过 CLI

```bash
# 通过 RPC 调用 (需启动 acorn-agent)
acorn-agent call echo --args '{"message": "Hello, Acorn!"}'
```

### 通过 Python API

```python
from acorn_core import Acorn, Task

acorn = Acorn()
acorn.load_plugins()

task = Task(command="echo", args={"message": "Hello, Acorn!"})
response = acorn.execute(task)
print(response.data)  # Hello, Acorn!
```

### 通过 RPC 客户端

```python
from acorn_cli.client import AcornClient

client = AcornClient()
result = client.execute("echo", {"message": "hello"})
print(result)  # {"success": true, "data": "hello"}
```

## 作为模板

```bash
cp -r examples-plugin my-new-plugin
cd my-new-plugin
```

修改 `pyproject.toml` 中的 name 和 entry-points，以及 `src/examples_plugin/echo.py` 中的插件实现。

## 目录结构

```
examples-plugin/
├── pyproject.toml
├── README.md
└── src/
    └── examples_plugin/
        ├── __init__.py
        ├── echo.py           # 插件实现
        └── cli.py            # CLI 命令 (可选)
```

## Entry Points

```toml
# pyproject.toml
[project.entry-points."yapex.acorn.plugins"]
examples = "examples_plugin:plugin"

# 可选：贡献 CLI 命令
[project.entry-points."acorn.cli.commands"]
example = "examples_plugin.cli:app"
```
