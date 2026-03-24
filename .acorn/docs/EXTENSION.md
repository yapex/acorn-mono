# Acorn 扩展规范

## 三种扩展机制

| 机制 | 扩展时机 | 用途 | 特点 |
|------|---------|------|------|
| **entry_points** | 打包时静态 | CLI 子命令扩展 | 独立 Typer app |
| **pluggy hooks** | 运行时动态 | 核心能力扩展 | 同步返回结果 |
| **event_bus** | 运行时动态 | 跨插件通信 | 解耦、观察者模式 |

---

## 1. CLI 命令扩展 → entry_points

### 使用场景
贡献独立的子命令，用户通过 `acorn <my-command>` 直接调用。

### 定义方式
在插件的 `pyproject.toml` 中定义：

```toml
[project.entry-points."acorn.cli.commands"]
vi = "vi_core.cli:app"
echo = "examples_plugin.cli:app"
```

### 实现方式
创建独立的 Typer app：

```python
# my_plugin/cli.py
import typer
app = typer.Typer(name="my-cmd", help="My command")

@app.command()
def query(symbol: str, years: int = 10):
    """查询数据"""
    ...
```

---

## 2. 核心能力扩展 → pluggy hooks

### 使用场景
系统需要收集各插件的能力，或调用插件的执行逻辑。

### 定义方式
在 `vi_core/spec.py` 中定义 hook 规范：

```python
class CalculatorSpec:
    @vi_hookspec
    def vi_list_calculators(self) -> list[dict]:
        """返回计算器列表"""
        return []
    
    @vi_hookspec(firstresult=True)
    def vi_run_calculator(self, name: str, data: dict, config: dict):
        """执行计算器"""
        return None
```

### 实现方式
在插件中实现 hook：

```python
class MyPlugin:
    @vi_hookimpl
    def vi_status(self) -> dict:
        """返回插件状态"""
        return {
            "name": "my_plugin",
            "description": "我的插件",
            "capabilities": {
                "calculators": [...],
                "fields": [...],
            }
        }
```

---

## 3. 跨插件通信 → event_bus

### 使用场景
- 通知事件（某事发生）
- 追踪系统状态（痛觉反馈）
- 解耦通信（发布-订阅）

### 事件常量
所有事件都应使用 `AcornEvents` 常量，禁止硬编码字符串：

```python
from acorn_events import EventBus, AcornEvents

# 订阅
@EventBus.on(AcornEvents.CALCULATOR_EXTENSION_NEEDED)
def on_extension_needed(event_type, sender, **kwargs):
    calculator_name = kwargs.get("calculator_name")

# 发布
EventBus.publish(AcornEvents.FIELD_UNSUPPORTED, sender=self, symbol="600519", fields=[...])
```

### 可用事件

| 常量 | 事件名 | 触发时机 | 典型订阅者 |
|------|--------|---------|-----------|
| `FIELD_UNSUPPORTED` | `vi.field.unsupported` | 请求字段不在标准定义中 | EvoManager |
| `FIELD_UNFILLED` | `vi.field.unfilled` | 字段在标准中但 Provider 不支持 | EvoManager |
| `CALCULATOR_EXTENSION_NEEDED` | `calculator.extension_needed` | 请求的计算器不存在 | EvoManager |
| `CALCULATOR_REGISTERED` | `calculator.registered` | 计算器注册成功 | - |
| `SYSTEM_STARTUP` | `system.startup` | 系统启动完成 | - |
| `SYSTEM_SHUTDOWN` | `system.shutdown` | 系统关闭 | - |
| `PLUGIN_LOADED` | `acorn.plugin.loaded` | 插件加载完成 | - |

---

## 决策树

```
需要扩展系统能力？
         │
         ├── 是，用户需要直接交互的子命令？
         │         └── entry_points (pyproject.toml)
         │
         ├── 是，需要同步返回结果？
         │         └── pluggy hooks (vi_hookspec)
         │
         └── 只是想知道某事发生了？
                   └── event_bus (AcornEvents 常量)
```

---

## 示例：创建新的计算器插件

### 1. CLI 命令 (entry_points)
```toml
[project.entry-points."acorn.cli.commands"]
my-calc = "my_calc.cli:app"
```

### 2. 计算器能力 (pluggy hooks)
```python
# my_calc/plugin.py
from vi_core.spec import vi_hookimpl, CalculatorSpec

class MyCalcPlugin(CalculatorSpec):
    @vi_hookimpl
    def vi_list_calculators(self):
        return [{"name": "my_ratio", "required_fields": ["a", "b"]}]
    
    @vi_hookimpl
    def vi_run_calculator(self, name, data, config):
        if name == "my_ratio":
            return data["a"] / data["b"]
```

### 3. 事件追踪 (event_bus)
```python
def on_load(self):
    from acorn_events import EventBus, AcornEvents
    EventBus.on(AcornEvents.CALCULATOR_REGISTERED)(self._on_calc_registered)
```
