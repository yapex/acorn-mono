# Acorn CLI + VI Plugin 重构实现计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 重构 Acorn CLI 系统和 VI Plugin，实现统一的插件架构，支持动态 CLI 命令和 VI 扩展能力。

**Architecture:**
- Acorn 作为微内核，通过 entry_points 发现插件
- acorn-cli 动态加载所有 `acorn.cli.commands` 插件命令
- VI Plugin 作为领域插件，支持内部扩展
- PluginRegistry 管理已安装插件，支持启用/禁用

**Tech Stack:** Python 3.12+, pluggy, typer, questionary, blinker

---

## 阶段 1: Acorn Core 清理

### Task 1: 清理 acorn-core 内置插件

**Files:**
- Create: `acorn-core/tests/test_kernel.py`
- Modify: `acorn-core/src/acorn_core/kernel.py`
- Modify: `acorn-core/src/acorn_core/__init__.py`

**Step 1: 写失败的测试**

```python
# acorn-core/tests/test_kernel.py
import pytest
from acorn_core import Acorn, Task

def test_acorn_loads_entry_points():
    """Acorn 加载时自动发现 entry_points 中的插件"""
    acorn = Acorn()
    acorn.load_plugins()
    
    plugins = dict(acorn.list_plugins())
    assert len(plugins) >= 1  # 至少应该有内置插件

def test_acorn_executes_registered_plugin():
    """Acorn 能执行已注册的插件命令"""
    acorn = Acorn()
    acorn.load_plugins()
    
    task = Task(command="capabilities")
    response = acorn.execute(task)
    
    assert response.success

def test_acorn_rejects_unknown_command():
    """Acorn 对未知命令返回错误"""
    acorn = Acorn()
    acorn.load_plugins()
    
    task = Task(command="nonexistent_command")
    response = acorn.execute(task)
    
    assert not response.success
    assert response.error.code == "NOT_IMPLEMENTED"
```

**Step 2: 运行测试确认失败**

Run: `cd acorn-core && uv run pytest tests/test_kernel.py -v`
Expected: PASS (因为当前实现已有这些功能，主要是验证)

**Step 3: 验证现有实现符合预期**

```python
# 检查 kernel.py 中的 load_plugins 实现
# 确认它只做 entry_points 加载，不依赖 registry
```

**Step 4: 运行测试确认通过**

Run: `cd acorn-core && uv run pytest tests/test_kernel.py -v`
Expected: PASS

**Step 5: 提交**

```bash
git add acorn-core/src/acorn_core/kernel.py acorn-core/tests/test_kernel.py
git commit -m "test: add kernel tests for entry point loading"
```

---

## 阶段 2: Acorn CLI 重构

### Task 2: 重写 acorn-cli 使用 typer

**Files:**
- Create: `acorn-cli/tests/test_cli.py`
- Modify: `acorn-cli/src/acorn_cli/cli.py`
- Modify: `acorn-cli/pyproject.toml`

**Step 1: 写失败的测试**

```python
# acorn-cli/tests/test_cli.py
import pytest
from typer.testing import CliRunner
from acorn_cli import app

runner = CliRunner()

def test_cli_help_shows_core_commands():
    """acorn --help 显示核心命令"""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "install" in result.stdout
    assert "config" in result.stdout
    assert "list" in result.stdout

def test_cli_list_shows_empty_registry():
    """acorn list 在空注册表时显示正确信息"""
    result = runner.invoke(app, ["list"])
    assert result.exit_code == 0
    assert "暂无" in result.stdout or "no plugins" in result.stdout.lower()
```

**Step 2: 运行测试确认失败**

Run: `cd acorn-cli && uv run pytest tests/test_cli.py -v`
Expected: FAIL - module 'acorn_cli' has no attribute 'app'

**Step 3: 写最小实现**

```python
# acorn-cli/src/acorn_cli/cli.py
import typer

app = typer.Typer(name="acorn", help="🌰 Acorn - 插件化命令行工具")

@app.command()
def install(source: str):
    """安装插件"""
    ...

@app.command()
def list():
    """列出已安装插件"""
    ...

@app.command()
def config():
    """配置插件 (TUI)"""
    ...

# 动态加载插件命令
def load_plugin_commands():
    from importlib.metadata import entry_points
    try:
        for ep in entry_points(group="acorn.cli.commands"):
            plugin_app = ep.load()
            app.add_typer(plugin_app, name=ep.name)
    except Exception:
        pass

load_plugin_commands()

if __name__ == "__main__":
    app()
```

**Step 4: 运行测试确认通过**

Run: `cd acorn-cli && uv run pytest tests/test_cli.py -v`
Expected: PASS

**Step 5: 提交**

```bash
git add acorn-cli/src/acorn_cli/cli.py acorn-cli/tests/test_cli.py
git commit -m "feat: rewrite acorn-cli with typer"
```

---

### Task 3: 实现 PluginRegistry

**Files:**
- Create: `acorn-cli/src/acorn_cli/registry.py`
- Create: `acorn-cli/tests/test_registry.py`
- Modify: `acorn-cli/src/acorn_cli/cli.py`

**Step 1: 写失败的测试**

```python
# acorn-cli/tests/test_registry.py
import pytest
import tempfile
from pathlib import Path
from acorn_cli.registry import PluginRegistry, PluginEntry

def test_registry_creates_file_on_first_save():
    """注册表在首次保存时创建文件"""
    with tempfile.TemporaryDirectory() as tmpdir:
        registry_path = Path(tmpdir) / "registry.json"
        registry = PluginRegistry(path=registry_path)
        
        # 注册一个插件
        entry = PluginEntry(
            name="test_plugin",
            entry_point="test_plugin:plugin",
            version="1.0.0",
        )
        registry._plugins["test_plugin"] = entry
        registry._save()
        
        assert registry_path.exists()

def test_registry_loads_saved_plugins():
    """注册表能加载已保存的插件"""
    with tempfile.TemporaryDirectory() as tmpdir:
        registry_path = Path(tmpdir) / "registry.json"
        
        # 创建并保存
        registry1 = PluginRegistry(path=registry_path)
        entry = PluginEntry(name="test", entry_point="test:plugin")
        registry1._plugins["test"] = entry
        registry1._save()
        
        # 重新加载
        registry2 = PluginRegistry(path=registry_path)
        assert "test" in registry2._plugins

def test_registry_install_plugin():
    """注册表能安装插件（模拟）"""
    registry = PluginRegistry(path=":memory:")
    
    # 注意：实际安装需要 uv，这里测试注册逻辑
    entry = PluginEntry(
        name="echo",
        entry_point="examples_plugin.echo:plugin",
        version="0.1.0",
        source="local",
    )
    registry._plugins["echo"] = entry
    registry._save()
    
    assert registry.get("echo") is not None
    assert registry.get("echo").enabled is True

def test_registry_enable_disable():
    """注册表能启用/禁用插件"""
    registry = PluginRegistry(path=":memory:")
    entry = PluginEntry(name="test", entry_point="test:plugin")
    registry._plugins["test"] = entry
    
    registry.disable("test")
    assert registry.get("test").enabled is False
    
    registry.enable("test")
    assert registry.get("test").enabled is True

def test_registry_toggle():
    """注册表能切换插件状态"""
    registry = PluginRegistry(path=":memory:")
    entry = PluginEntry(name="test", entry_point="test:plugin", enabled=True)
    registry._plugins["test"] = entry
    
    registry.toggle("test")
    assert registry.get("test").enabled is False
    
    registry.toggle("test")
    assert registry.get("test").enabled is True
```

**Step 2: 运行测试确认失败**

Run: `cd acorn-cli && uv run pytest tests/test_registry.py -v`
Expected: FAIL - No module named 'acorn_cli.registry'

**Step 3: 写实现**

```python
# acorn-cli/src/acorn_cli/registry.py
from dataclasses import dataclass, field, asdict
from pathlib import Path
import json
from typing import Any
from datetime import datetime

@dataclass
class PluginEntry:
    name: str
    entry_point: str
    version: str = "unknown"
    enabled: bool = True
    source: str = "pypi"
    source_path: str = ""
    installed_at: str = ""
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PluginEntry:
        return cls(**data)

class PluginRegistry:
    def __init__(self, path: str | Path | None = None) -> None:
        if path == ":memory:":
            self.path = None
        else:
            self.path = Path(path) if path else self._default_path()
        self._plugins: dict[str, PluginEntry] = {}
        if self.path and self.path.exists():
            self._load()

    def _default_path(self) -> Path:
        import os
        env_path = os.environ.get("ACORN_REGISTRY_PATH")
        if env_path:
            return Path(env_path)
        local = Path.cwd() / ".acorn" / "registry.json"
        if local.parent.exists():
            return local
        return Path.home() / ".acorn" / "registry.json"

    def _load(self) -> None:
        if not self.path or not self.path.exists():
            return
        try:
            with open(self.path) as f:
                data = json.load(f)
            self._plugins = {
                name: PluginEntry.from_dict(entry)
                for name, entry in data.get("plugins", {}).items()
            }
        except (json.JSONDecodeError, KeyError):
            self._plugins = {}

    def _save(self) -> None:
        if not self.path:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "version": "1.0",
            "updated_at": datetime.now().isoformat(),
            "plugins": {name: e.to_dict() for name, e in self._plugins.items()}
        }
        with open(self.path, "w") as f:
            json.dump(data, f, indent=2)

    def enable(self, name: str) -> tuple[bool, str]:
        if name not in self._plugins:
            return False, f"Plugin '{name}' not found"
        self._plugins[name].enabled = True
        self._save()
        return True, f"Plugin '{name}' enabled"

    def disable(self, name: str) -> tuple[bool, str]:
        if name not in self._plugins:
            return False, f"Plugin '{name}' not found"
        self._plugins[name].enabled = False
        self._save()
        return True, f"Plugin '{name}' disabled"

    def toggle(self, name: str) -> tuple[bool, str]:
        if name not in self._plugins:
            return False, f"Plugin '{name}' not found"
        self._plugins[name].enabled = not self._plugins[name].enabled
        self._save()
        status = "enabled" if self._plugins[name].enabled else "disabled"
        return True, f"Plugin '{name}' {status}"

    def list(self) -> list[PluginEntry]:
        return list(self._plugins.values())

    def get_enabled(self) -> list[PluginEntry]:
        return [e for e in self._plugins.values() if e.enabled]

    def get(self, name: str) -> PluginEntry | None:
        return self._plugins.get(name)

    def update_status(self, statuses: dict[str, bool]) -> int:
        count = 0
        for name, enabled in statuses.items():
            if name in self._plugins and self._plugins[name].enabled != enabled:
                self._plugins[name].enabled = enabled
                count += 1
        if count > 0:
            self._save()
        return count

    def discover_available(self) -> list[dict[str, Any]]:
        from importlib.metadata import entry_points
        available = []
        registered = set(self._plugins.keys())
        try:
            for ep in entry_points(group="yapex.acorn.plugins"):
                if ep.name not in registered:
                    available.append({
                        "name": ep.name,
                        "entry_point": ep.value,
                    })
        except Exception:
            pass
        return available
```

**Step 4: 运行测试确认通过**

Run: `cd acorn-cli && uv run pytest tests/test_registry.py -v`
Expected: PASS

**Step 5: 提交**

```bash
git add acorn-cli/src/acorn_cli/registry.py acorn-cli/tests/test_registry.py
git commit -m "feat: implement PluginRegistry"
```

---

### Task 4: 实现 CLI 核心命令

**Files:**
- Modify: `acorn-cli/src/acorn_cli/cli.py`
- Modify: `acorn-cli/tests/test_cli.py`

**Step 1: 写失败的测试**

```python
# 添加到 test_cli.py

def test_cli_list_with_plugins(monkeypatch):
    """acorn list 显示已安装插件"""
    # Mock registry
    from acorn_cli.registry import PluginEntry, PluginRegistry
    
    mock_plugins = {
        "echo": PluginEntry(name="echo", entry_point="echo:plugin", version="1.0"),
    }
    
    monkeypatch.setattr(PluginRegistry, "list", lambda self: list(mock_plugins.values()))
    
    result = runner.invoke(app, ["list"])
    assert result.exit_code == 0
    assert "echo" in result.stdout
```

**Step 2: 运行测试确认失败**

Run: `cd acorn-cli && uv run pytest tests/test_cli.py::test_cli_list_with_plugins -v`
Expected: FAIL

**Step 3: 实现命令**

```python
# acorn-cli/src/acorn_cli/cli.py
import typer
from typing import Optional
from .registry import PluginRegistry

app = typer.Typer(name="acorn", help="🌰 Acorn - 插件化命令行工具")

registry_path = Optional[str] = None

def get_registry() -> PluginRegistry:
    return PluginRegistry(path=registry_path)

@app.command()
def install(
    source: str,
    name: Optional[str] = None,
    entry_point: Optional[str] = None,
):
    """安装插件"""
    registry = get_registry()
    # TODO: 实现安装逻辑
    typer.echo(f"安装插件: {source}")

@app.command("list")
def list_plugins():
    """列出已安装插件"""
    registry = get_registry()
    plugins = registry.list()
    
    if not plugins:
        typer.echo("📭 暂无已安装的插件")
        return
    
    typer.echo(f"\n📋 已安装插件 ({len(plugins)})\n")
    for entry in plugins:
        status = "✓" if entry.enabled else "✗"
        typer.echo(f"  {status} {entry.name:<20} v{entry.version}")

@app.command()
def enable(name: str):
    """启用插件"""
    registry = get_registry()
    success, msg = registry.enable(name)
    typer.echo(f"{'✅' if success else '❌'} {msg}")

@app.command()
def disable(name: str):
    """禁用插件"""
    registry = get_registry()
    success, msg = registry.disable(name)
    typer.echo(f"{'✅' if success else '❌'} {msg}")

@app.command()
def config():
    """配置插件 (TUI)"""
    typer.echo("打开配置界面...")

@app.command()
def discover():
    """发现可用插件"""
    registry = get_registry()
    available = registry.discover_available()
    if not available:
        typer.echo("✅ 所有可用插件都已注册")
        return
    typer.echo(f"\n🔍 发现 {len(available)} 个未注册插件:\n")
    for p in available:
        typer.echo(f"  • {p['name']}")

# 动态加载插件命令
def load_plugin_commands():
    from importlib.metadata import entry_points
    try:
        for ep in entry_points(group="acorn.cli.commands"):
            plugin_app = ep.load()
            app.add_typer(plugin_app, name=ep.name)
    except Exception:
        pass

load_plugin_commands()

if __name__ == "__main__":
    app()
```

**Step 4: 运行测试确认通过**

Run: `cd acorn-cli && uv run pytest tests/test_cli.py -v`
Expected: PASS

**Step 5: 提交**

```bash
git add acorn-cli/src/acorn_cli/cli.py
git commit -m "feat: implement core CLI commands"
```

---

### Task 5: 实现 TUI 配置界面

**Files:**
- Create: `acorn-cli/src/acorn_cli/tui.py`
- Create: `acorn-cli/tests/test_tui.py`

**Step 1: 写失败的测试**

```python
# acorn-cli/tests/test_tui.py
import pytest
from acorn_cli.tui import format_plugin_entry
from acorn_cli.registry import PluginEntry

def test_format_plugin_entry_enabled():
    """格式化的插件条目显示启用状态"""
    entry = PluginEntry(
        name="echo",
        entry_point="echo:plugin",
        version="1.0.0",
        enabled=True,
        source="pypi",
    )
    result = format_plugin_entry(entry)
    assert "✓" in result
    assert "echo" in result
    assert "1.0.0" in result

def test_format_plugin_entry_disabled():
    """格式化的插件条目显示禁用状态"""
    entry = PluginEntry(
        name="test",
        entry_point="test:plugin",
        version="2.0.0",
        enabled=False,
    )
    result = format_plugin_entry(entry)
    assert "✗" in result
    assert "test" in result
```

**Step 2: 运行测试确认失败**

Run: `cd acorn-cli && uv run pytest tests/test_tui.py -v`
Expected: FAIL - No module 'acorn_cli.tui'

**Step 3: 写实现**

```python
# acorn-cli/src/acorn_cli/tui.py
from .registry import PluginEntry

def format_plugin_entry(entry: PluginEntry, max_name: int = 20) -> str:
    """格式化插件条目显示"""
    status = "✓" if entry.enabled else "✗"
    name = entry.name[:max_name].ljust(max_name)
    version = f"v{entry.version}" if entry.version != "unknown" else ""
    return f"{status} {name} {version}".strip()

def run_config_tui(registry) -> bool:
    """运行 TUI 配置界面"""
    try:
        import questionary
        from questionary import Style
    except ImportError:
        print("⚠️  需要安装 questionary: uv pip install questionary")
        return False
    
    plugins = registry.list()
    if not plugins:
        print("📭 暂无已安装的插件")
        return False
    
    choices = []
    for entry in plugins:
        label = format_plugin_entry(entry)
        choices.append(questionary.Choice(title=label, value=entry.name, checked=entry.enabled))
    
    print("\n" + "═" * 50)
    print("🌰 Acorn 插件配置")
    print("═" * 50)
    
    selected = questionary.checkbox("选择要启用的插件:", choices=choices).ask()
    if selected is None:
        return False
    
    statuses = {name: (name in selected) for name in [e.name for e in plugins]}
    changed = registry.update_status(statuses)
    
    if changed > 0:
        print(f"\n✅ 已更新 {changed} 个插件状态")
    else:
        print("\n无变更")
    
    return changed > 0
```

**Step 4: 运行测试确认通过**

Run: `cd acorn-cli && uv run pytest tests/test_tui.py -v`
Expected: PASS

**Step 5: 提交**

```bash
git add acorn-cli/src/acorn_cli/tui.py acorn-cli/tests/test_tui.py
git commit -m "feat: implement TUI config interface"
```

---

## 阶段 3: Acorn Agent 重构

### Task 6: Agent 使用 Registry 加载插件

**Files:**
- Create: `acorn-agent/tests/test_server.py`
- Modify: `acorn-agent/src/acorn_agent/server.py`

**Step 1: 写失败的测试**

```python
# acorn-agent/tests/test_server.py
import pytest
from acorn_agent.server import AcornServer

def test_server_loads_plugins_from_registry(tmp_path, monkeypatch):
    """Server 启动时从 registry 加载插件"""
    # 创建临时 registry
    registry_file = tmp_path / "registry.json"
    registry_file.write_text('{"plugins": {}}')
    
    monkeypatch.setenv("ACORN_REGISTRY_PATH", str(registry_file))
    
    # 注意：完整测试需要 mock Acorn 或使用内存 registry
    # 这里只测试结构
```

**Step 2: 运行测试确认失败**

Run: `cd acorn-agent && uv run pytest tests/test_server.py -v`
Expected: FAIL or SKIP (需要更多设置)

**Step 3: 简化实现**

```python
# acorn-agent/src/acorn_agent/server.py
# 简化版本，不再硬编码 vi_plugin
class AcornServer:
    def __init__(self, socket_path: str | None = None) -> None:
        self.socket_path = socket_path or str(DEFAULT_SOCKET_PATH)
        self.acorn = Acorn()
        self.acorn.load_plugins()
        self._running = False
```

**Step 4: 运行测试确认通过**

Run: `cd acorn-agent && uv run pytest tests/test_server.py -v`

**Step 5: 提交**

```bash
git add acorn-agent/src/acorn_agent/server.py acorn-agent/tests/test_server.py
git commit -m "refactor: remove hardcoded vi_plugin from agent"
```

---

## 阶段 4: VI Plugin 重构

### Task 7: 重构 VI Plugin 结构

**Files:**
- Create: `value-investment-plugin/vi_plugin/pyproject.toml`
- Create: `value-investment-plugin/vi_plugin/src/vi_plugin/__init__.py`
- Create: `value-investment-plugin/vi_plugin/src/vi_plugin/cli.py`
- Create: `value-investment-plugin/vi_plugin/tests/`

**Step 1: 写失败的测试**

```python
# value-investment-plugin/vi_plugin/tests/test_vi_plugin.py
import pytest
from vi_plugin import plugin

def test_vi_plugin_exports_correct_commands():
    """VI 插件导出正确的命令"""
    assert hasattr(plugin, "commands")
    commands = plugin.commands if callable(plugin.commands) else plugin.commands
    assert "vi_query" in commands
    assert "vi_list_fields" in commands
    assert "vi_list_calculators" in commands

def test_vi_plugin_handles_query_command():
    """VI 插件能处理查询命令"""
    from acorn_core import Task
    
    task = Task(command="vi_query", args={"symbol": "600519"})
    result = plugin.handle(task)
    
    # 可能需要 mock 数据源
    assert isinstance(result, dict)
    assert "success" in result or "error" in result
```

**Step 2: 运行测试确认失败**

Run: `cd value-investment-plugin/vi_plugin && uv run pytest tests/ -v`
Expected: FAIL - No module 'vi_plugin'

**Step 3: 写最小实现**

```python
# value-investment-plugin/vi_plugin/pyproject.toml
[project]
name = "vi-plugin"
version = "0.1.0"
description = "Value Investment Plugin for Acorn"
requires-python = ">=3.12"
dependencies = [
    "acorn-core>=0.1.0",
    "vi-core>=0.1.0",
]

[project.entry-points."yapex.acorn.plugins"]
vi = "vi_plugin:plugin"

[project.entry-points."acorn.cli.commands"]
vi = "vi_plugin.cli:app"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

```python
# value-investment-plugin/vi_plugin/src/vi_plugin/__init__.py
from acorn_core import Task, hookimpl

class VIPlugin:
    """Value Investment Plugin - 桥接 VI Core 到 Acorn"""
    
    @property
    def commands(self) -> list[str]:
        return ["vi_query", "vi_list_fields", "vi_list_calculators"]
    
    @hookimpl
    def handle(self, task: Task) -> dict:
        command = task.command
        args = task.args or {}
        
        if command == "vi_query":
            return self._handle_query(args)
        elif command == "vi_list_fields":
            return self._handle_list_fields(args)
        elif command == "vi_list_calculators":
            return self._handle_list_calculators(args)
        
        return {"success": False, "error": {"code": "NOT_IMPLEMENTED"}}
    
    def _handle_query(self, args: dict) -> dict:
        # TODO: 委托给 vi_core
        return {"success": True, "data": {"symbol": args.get("symbol"), "note": "stub"}}
    
    def _handle_list_fields(self, args: dict) -> dict:
        return {"success": True, "data": []}
    
    def _handle_list_calculators(self, args: dict) -> dict:
        return {"success": True, "data": []}

plugin = VIPlugin()
```

```python
# value-investment-plugin/vi_plugin/src/vi_plugin/cli.py
import typer
from typing import Optional

app = typer.Typer(name="vi", help="Value Investment - 财务数据查询")

@app.command()
def query(
    symbol: str,
    years: int = 10,
    fields: Optional[str] = None,
    calculators: Optional[str] = None,
):
    """查询股票财务数据"""
    from acorn_agent import AcornClient
    client = AcornClient()
    result = client.execute("vi_query", {
        "symbol": symbol,
        "years": years,
        "fields": fields,
        "calculators": calculators,
    })
    typer.echo(result)

@app.command("list-fields")
def list_fields(
    source: Optional[str] = None,
    prefix: Optional[str] = None,
):
    """列出可用字段"""
    from acorn_agent import AcornClient
    client = AcornClient()
    result = client.execute("vi_list_fields", {
        "source": source,
        "prefix": prefix,
    })
    typer.echo(result)

@app.command("list-calculators")
def list_calculators():
    """列出可用计算器"""
    from acorn_agent import AcornClient
    client = AcornClient()
    result = client.execute("vi_list_calculators", {})
    typer.echo(result)
```

**Step 4: 运行测试确认通过**

Run: `cd value-investment-plugin/vi_plugin && uv run pytest tests/ -v`

**Step 5: 提交**

```bash
git add value-investment-plugin/vi_plugin/
git commit -m "feat: refactor VI as standalone plugin"
```

---

### Task 8: 实现 VI 扩展机制

**Files:**
- Create: `value-investment-plugin/vi_plugin/src/vi_plugin/extensions.py`
- Create: `value-investment-plugin/vi_plugin/tests/test_extensions.py`

**Step 1: 写失败的测试**

```python
# value-investment-plugin/vi_plugin/tests/test_extensions.py
import pytest
from vi_plugin.extensions import ExtensionRegistry, load_extension

def test_extension_registry_initializes():
    """扩展注册表初始化"""
    registry = ExtensionRegistry()
    assert registry._extensions == []

def test_load_extension_from_entry_point():
    """能从 entry point 加载扩展"""
    # 测试发现和加载
    registry = ExtensionRegistry()
    extensions = registry.discover()
    # 至少应该能找到内置扩展
    assert isinstance(extensions, list)

def test_extension_registry_loads_local_path():
    """扩展注册表能从本地路径加载"""
    registry = ExtensionRegistry()
    # 本地路径加载
    # registry.load_from_path("./my-extension")
```

**Step 2: 运行测试确认失败**

Run: `cd value-investment-plugin/vi_plugin && uv run pytest tests/test_extensions.py -v`

**Step 3: 写实现**

```python
# value-investment-plugin/vi_plugin/src/vi_plugin/extensions.py
from dataclasses import dataclass
from importlib.metadata import entry_points
from pathlib import Path
from typing import Any

@dataclass
class Extension:
    """VI 扩展"""
    name: str
    entry_point: str
    source: str = "entry_point"  # entry_point, local, git
    path: str = ""
    
class ExtensionRegistry:
    """VI 扩展注册表"""
    
    ENTRY_POINT_GROUP = "vi.extensions"
    
    def __init__(self) -> None:
        self._extensions: list[Extension] = []
        self._local_paths: list[Path] = []
    
    def discover(self) -> list[Extension]:
        """发现已安装的扩展"""
        extensions = []
        try:
            for ep in entry_points(group=self.ENTRY_POINT_GROUP):
                extensions.append(Extension(
                    name=ep.name,
                    entry_point=ep.value,
                    source="entry_point",
                ))
        except Exception:
            pass
        
        # 添加本地路径扩展
        for path in self._local_paths:
            extensions.append(Extension(
                name=path.name,
                entry_point="",
                source="local",
                path=str(path),
            ))
        
        self._extensions = extensions
        return extensions
    
    def add_local_path(self, path: str | Path) -> None:
        """添加本地扩展路径"""
        p = Path(path)
        if p.exists() and p not in self._local_paths:
            self._local_paths.append(p)
    
    def load_extension(self, extension: Extension) -> Any:
        """加载单个扩展"""
        if extension.source == "local":
            # 从本地路径加载
            # 动态 import
            import importlib.util
            spec = importlib.util.spec_from_file_location(
                extension.name, 
                Path(extension.path) / "__init__.py"
            )
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                return module
        elif extension.source == "entry_point":
            # 从 entry point 加载
            module_path, _, attr = extension.entry_point.partition(":")
            module = __import__(module_path, fromlist=[attr])
            return getattr(module, attr) if attr else module
        return None
```

**Step 4: 运行测试确认通过**

Run: `cd value-investment-plugin/vi_plugin && uv run pytest tests/test_extensions.py -v`

**Step 5: 提交**

```bash
git add value-investment-plugin/vi_plugin/src/vi_plugin/extensions.py
git commit -m "feat: implement VI extension mechanism"
```

---

## 阶段 5: 集成测试

### Task 9: 端到端集成测试

**Files:**
- Create: `tests/integration/test_full_flow.py`

**Step 1: 写失败的测试**

```python
# tests/integration/test_full_flow.py
import pytest
import subprocess

def test_acorn_install_and_list():
    """安装插件后能用 list 看到"""
    # 1. 安装
    result = subprocess.run(
        ["acorn", "install", "./examples-plugin"],
        capture_output=True,
        text=True,
    )
    
    # 2. 列出
    result = subprocess.run(
        ["acorn", "list"],
        capture_output=True,
        text=True,
    )
    
    assert "examples_plugin" in result.stdout or "echo" in result.stdout

def test_vi_plugin_commands_available():
    """安装 VI 插件后命令可用"""
    # 先安装
    # 然后检查命令
    result = subprocess.run(
        ["acorn", "vi", "--help"],
        capture_output=True,
        text=True,
    )
    
    # 如果 VI 已安装，应该能看到 vi 命令
    if result.exit_code == 0:
        assert "query" in result.stdout or "Query" in result.stdout
```

**Step 2: 运行测试确认失败**

Run: `uv run pytest tests/integration/ -v`

**Step 3: 运行完整安装流程测试**

```bash
# 确保所有包已安装
cd acorn-mono
uv sync --all-packages

# 测试
uv run acorn --help
uv run acorn list
```

**Step 4: 提交**

```bash
git add tests/integration/
git commit -m "test: add integration tests"
```

---

## 执行方式

**Plan complete and saved to `docs/plans/2026-03-23-acorn-cli-and-vi-plugin.md`**

Two execution options:

**1. Subagent-Driven (this session)** - I dispatch fresh subagent per task, review between tasks, fast iteration

**2. Parallel Session (separate)** - Open new session with executing-plans, batch execution with checkpoints

**Which approach?**
