---
name: pluggy-plugin-dev
description: Guide for writing pluggy plugins. Use when creating or developing a new plugin for the Acorn system.
---

# Pluggy Plugin Development Guide

## Project Structure

```
my-plugin/
├── pyproject.toml
└── src/
    └── my_plugin/
        └── __init__.py
```

## 1. pyproject.toml

```toml
[project]
name = "my-plugin"
version = "0.1.0"
requires-python = ">=3.12"

[project.entry-points."yapex.acorn.plugins"]
my_command = "my_plugin:plugin"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/my_plugin"]
```

## 2. Plugin Implementation

```python
from acorn_core.specs import hookimpl

class MyPlugin:
    @property
    def commands(self) -> list[str]:
        return ["my_command"]

    @hookimpl
    def get_capabilities(self) -> dict:
        return {
            "commands": ["my_command"],
            "args": {
                "param": {"type": "string", "required": True}
            }
        }

    @hookimpl
    def handle(self, task) -> dict:
        param = task.args.get("param")
        return {
            "success": True,
            "data": f"Result: {param}"
        }

plugin = MyPlugin()
```

## 3. Hook Specs

| Hook | Required | Description |
|------|----------|-------------|
| `commands` (property) | Yes | Returns list of command names |
| `handle(task)` | Yes | Processes task, returns dict |
| `get_capabilities()` | No | Declares capabilities |
| `on_load()` | No | Called when plugin loads |
| `on_unload()` | No | Called when plugin unloads |

## 4. Response Format

```python
# Success
return {"success": True, "data": "result"}

# Error
return {"success": False, "error": {"code": "ERROR_CODE", "message": "error message"}}
# Or simple format
return {"success": False, "error": "ERROR_CODE: error message"}
```

## 5. Install & Test

```bash
# Install
uv pip install -e .

# Test
cd acorn-core && uv run pytest tests/ -q
```
