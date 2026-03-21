# Examples Plugin 🌳

Acorn 官方示例插件，作为开发新插件的参考模板。

## 安装

```bash
uv pip install -e examples-plugin/
```

## 命令

| 命令 | 说明 | 参数 |
|------|------|------|
| `echo` | 回显消息 | `message` (string, required) |

## 使用

```python
from acorn_core import Acorn, Task

acorn = Acorn()
acorn.load_plugins()

task = Task(command="echo", args={"message": "Hello, Acorn!"})
response = acorn.execute(task)
print(response.data)  # Hello, Acorn!
```

## 通过 Agent 客户端

```python
from acorn_agent import AcornClient

client = AcornClient()
result = client("echo", message="hello")
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
        └── echo.py
```
