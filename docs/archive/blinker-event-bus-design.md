# Blinker 事件总线架构设计

> 基于 Blinker 的事件驱动架构，用于解耦业务层和进化层

## 1. 背景

### 1.1 当前架构

```
acorn-core (pluggy "evo")
  ├── kernel.py (load_plugins, execute)
  ├── evo_manager (Genes) ← 进化层
  └── vi_core (Genes) ← 通过 entry_points
        └── 子插件通过 vi_core 内部 pluggy 管理
              ├── vi_fields_ifrs
              ├── provider_tushare
              └── vi_calculators
```

**问题**：
1. 嵌套结构中，子插件的错误/需求无法到达 evo_manager
2. 业务层和进化层缺乏解耦机制
3. 进化能力无法感知业务层状态

### 1.2 目标架构

```
┌─────────────────────────────────────────────────────────────┐
│                      acorn-core                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                    EventBus (blinker)                │   │
│  │  - field_missing                                     │   │
│  │  - field_requested                                   │   │
│  │  - provider_error                                   │   │
│  │  - calculator_error                                 │   │
│  │  - plugin_loaded                                    │   │
│  └─────────────────────────────────────────────────────┘   │
│         ▲                    ▲                    ▲         │
│         │                    │                    │         │
│         │ send               │ send               │ subscribe│
│         │                    │                    │         │
│  ┌──────┴──────┐    ┌───────┴──────┐    ┌───────┴──────┐ │
│  │ vi_core     │    │ provider      │    │ evo_manager  │ │
│  │ (业务层)    │    │ _tushare       │    │ (进化层)     │ │
│  │             │    │ (子插件)       │    │              │ │
│  │ - 统一发送  │    │ - 发送错误    │    │ - 订阅所有   │ │
│  │   业务事件  │    │   事件        │    │   事件       │ │
│  └─────────────┘    └───────────────┘    └──────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### 1.3 核心设计原则

1. **事件统一入口**：vi_core 作为业务层统一入口，汇总子插件事件
2. **进化层被动感知**：evo_manager 只订阅，不主动轮询
3. **职责分离**：pluggy 管插件，blinker 管事件

## 2. 技术选型

### 2.1 Blinker 简介

| 特性 | 说明 |
|------|------|
| 全局信号注册表 | 通过名称获取同一信号对象 |
| 弱引用自动断开 | 订阅者被 GC 时自动断开 |
| 线程安全 | 支持多线程环境 |
| 返回值收集 | 接收器可返回值 |
| 广泛使用 | Flask、pytest 等项目都在用 |

### 2.2 pluggy vs blinker 职责边界

| 机制 | 职责 | 特点 |
|------|------|------|
| **pluggy** | 插件注册、生命周期、方法调用 | 同步调用，调用者等待结果 |
| **blinker** | 状态变更通知、跨层通信 | 异步通知，不阻塞主流程 |

## 3. 事件定义

### 3.1 事件列表

| 事件名 | 说明 | 触发者 | 订阅者 |
|--------|------|--------|--------|
| `field_missing` | 请求的字段不存在 | vi_core | evo_manager |
| `field_requested` | 字段被请求 | vi_core | evo_manager |
| `provider_error` | 数据源错误 | vi_core / provider | evo_manager |
| `calculator_error` | 计算器执行错误 | vi_core | evo_manager |
| `plugin_loaded` | 插件加载完成 | acorn-core | evo_manager |

### 3.2 事件数据结构 (dataclass)

```python
# acorn-core/src/acorn_core/events.py
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from blinker import signal

@dataclass
class Event:
    """事件基类"""
    timestamp: datetime = field(default_factory=datetime.now)
    source: str = ""  # 事件来源插件名

@dataclass
class FieldMissingEvent(Event):
    """字段缺失事件"""
    fields: list[str] = field(default_factory=list)
    symbol: str = ""
    context: dict[str, Any] = field(default_factory=dict)

@dataclass
class FieldRequestedEvent(Event):
    """字段请求事件"""
    fields: list[str] = field(default_factory=list)
    symbol: str = ""

@dataclass
class ProviderErrorEvent(Event):
    """数据源错误事件"""
    provider: str = ""
    error_type: str = ""
    error_message: str = ""
    symbol: str = ""

@dataclass
class CalculatorErrorEvent(Event):
    """计算器错误事件"""
    calculator: str = ""
    error_type: str = ""
    error_message: str = ""
    context: dict[str, Any] = field(default_factory=dict)

@dataclass
class PluginLoadedEvent(Event):
    """插件加载事件"""
    plugin_name: str = ""
    capabilities: dict[str, Any] = field(default_factory=dict)
```

## 4. 实现设计

### 4.1 事件总线模块

```python
# acorn-core/src/acorn_core/events.py
from __future__ import annotations
from dataclasses import asdict
from datetime import datetime
from typing import Any, Callable
from blinker import signal

class EventBus:
    """事件总线 - 基于 Blinker 的事件分发系统"""
    
    # 事件类型常量
    FIELD_MISSING = "field_missing"
    FIELD_REQUESTED = "field_requested"
    PROVIDER_ERROR = "provider_error"
    CALCULATOR_ERROR = "calculator_error"
    PLUGIN_LOADED = "plugin_loaded"
    
    @classmethod
    def emit(cls, event_type: str, sender: Any, **kwargs) -> list[tuple]:
        """
        发送事件
        
        Args:
            event_type: 事件类型
            sender: 发送者
            **kwargs: 事件数据
        
        Returns:
            [(receiver, return_value), ...]
        """
        return signal(event_type).send(sender, **kwargs)
    
    @classmethod
    def subscribe(cls, event_type: str) -> Callable:
        """
        订阅事件的装饰器
        
        Usage:
            @EventBus.subscribe(EventBus.FIELD_MISSING)
            def on_field_missing(sender, fields, **kwargs):
                print(f"Missing fields: {fields}")
        """
        def decorator(func: Callable) -> Callable:
            signal(event_type).connect(func)
            return func
        return decorator
    
    @classmethod
    def unsubscribe(cls, event_type: str, receiver: Callable) -> None:
        """取消订阅"""
        signal(event_type).disconnect(receiver)
```

### 4.2 vi_core 事件发送 (业务层融合)

**设计原则**：vi_core 作为业务层统一入口，汇总子插件事件后统一发送

```python
# value-investment-plugin/vi_core/src/vi_core/plugin.py
from acorn_core.events import EventBus

class ViCorePlugin:
    """VI Core plugin for acorn
    
    Implements Genes spec and manages VI sub-plugins.
    业务层统一事件入口。
    """
    
    # 内部 plugin manager
    _vi_pm: Any = None
    
    # =============================================================================
    # Genes Spec Implementation
    # =============================================================================
    
    @property
    def commands(self) -> list[str]:
        return ["vi_query", "vi_list_fields", "vi_list_calculators"]
    
    def handle(self, task: "Task") -> dict[str, Any]:
        """Handle VI commands"""
        command = task.command
        args = task.args or {}
        
        try:
            if command == "vi_query":
                return self._query(args)
            elif command == "vi_list_fields":
                return self._list_fields(args)
            elif command == "vi_list_calculators":
                return self._list_calculators(args)
            else:
                return {"success": False, "error": f"Unknown command: {command}"}
        except Exception as e:
            # 统一发送错误事件
            EventBus.emit(
                EventBus.ERROR_OCCURRED,
                sender=self,
                error_type=type(e).__name__,
                error_message=str(e),
                task={'command': command, 'args': args}
            )
            raise
    
    # =============================================================================
    # 业务事件发送
    # =============================================================================
    
    def _query(self, args: dict[str, Any]) -> dict[str, Any]:
        """查询财务数据"""
        symbol = args.get("symbol")
        fields_str = args.get("fields", "")
        
        # 解析字段
        requested = set(f.strip() for f in fields_str.split(",") if f.strip())
        
        if not requested:
            return {"success": False, "error": "No fields specified"}
        
        # 检查字段支持情况
        pm = self.get_vi_pm()
        supported_fields = self._get_supported_fields(pm)
        
        # 计算缺失字段
        missing_fields = requested - supported_fields
        if missing_fields:
            # 发送字段缺失事件
            EventBus.emit(
                EventBus.FIELD_MISSING,
                sender=self,
                fields=list(missing_fields),
                symbol=symbol,
                context=args
            )
        
        # 发送字段请求事件
        EventBus.emit(
            EventBus.FIELD_REQUESTED,
            sender=self,
            fields=list(requested),
            symbol=symbol
        )
        
        # 继续查询逻辑...
        # ...
    
    def _run_calculators(
        self,
        results: dict[str, Any],
        calculator_names: set[str],
        calculator_config: dict[str, Any],
    ) -> None:
        """运行计算器"""
        pm = self.get_vi_pm()
        
        # ... 计算器执行逻辑 ...
        
        # 捕获计算器错误并发送事件
        if calc_error:
            EventBus.emit(
                EventBus.CALCULATOR_ERROR,
                sender=self,
                calculator=calc_name,
                error_type=error_type,
                error_message=str(error),
                context={'data_keys': list(results.get('data', {}).keys())}
            )
    
    def _get_supported_fields(self, pm) -> set[str]:
        """获取所有支持的字段"""
        fields = set()
        for result in pm.hook.vi_supported_fields():
            if result:
                fields.update(result)
        return fields
```

### 4.3 evo_manager 事件订阅 (进化层融合)

**设计原则**：evo_manager 在 `__init__` 中订阅所有事件，不依赖 `on_load()`

```python
# acorn-core/src/acorn_core/plugins/evo_manager.py
from acorn_core.events import EventBus

class EvoManager:
    """进化管理器
    
    订阅所有业务事件，进行学习和分析。
    """
    
    def __init__(self):
        # 数据收集
        self.field_demand_log: dict[str, dict] = {}
        self.error_log: list[dict] = []
        self.capability_log: list[dict] = []
        
        # 在 __init__ 中订阅事件（不依赖 on_load）
        self._setup_event_subscriptions()
    
    def _setup_event_subscriptions(self):
        """设置事件订阅"""
        EventBus.subscribe(EventBus.FIELD_MISSING)(self.on_field_missing)
        EventBus.subscribe(EventBus.FIELD_REQUESTED)(self.on_field_requested)
        EventBus.subscribe(EventBus.PROVIDER_ERROR)(self.on_provider_error)
        EventBus.subscribe(EventBus.CALCULATOR_ERROR)(self.on_calculator_error)
        EventBus.subscribe(EventBus.PLUGIN_LOADED)(self.on_plugin_loaded)
        EventBus.subscribe(EventBus.ERROR_OCCURRED)(self.on_error)
    
    # =============================================================================
    # 事件处理器
    # =============================================================================
    
    def on_field_missing(self, sender, fields, symbol="", **kwargs):
        """处理字段缺失事件"""
        for field in fields:
            if field not in self.field_demand_log:
                self.field_demand_log[field] = {
                    'count': 0,
                    'symbols': set(),
                    'first_seen': datetime.now(),
                    'last_seen': None,
                }
            
            entry = self.field_demand_log[field]
            entry['count'] += 1
            entry['last_seen'] = datetime.now()
            if symbol:
                entry['symbols'].add(symbol)
    
    def on_field_requested(self, sender, fields, symbol="", **kwargs):
        """处理字段请求事件"""
        # 记录字段使用频率
        for field in fields:
            if field not in self.field_demand_log:
                self.field_demand_log[field] = {
                    'count': 0,
                    'symbols': set(),
                    'first_seen': datetime.now(),
                    'last_seen': None,
                }
            entry = self.field_demand_log[field]
            entry['count'] += 1
            entry['last_seen'] = datetime.now()
    
    def on_provider_error(self, sender, provider, error_type, error_message, symbol="", **kwargs):
        """处理数据源错误"""
        self.error_log.append({
            'timestamp': datetime.now(),
            'source': 'provider',
            'provider': provider,
            'error_type': error_type,
            'error_message': error_message,
            'symbol': symbol,
        })
        self._trim_error_log()
    
    def on_calculator_error(self, sender, calculator, error_type, error_message, **kwargs):
        """处理计算器错误"""
        self.error_log.append({
            'timestamp': datetime.now(),
            'source': 'calculator',
            'calculator': calculator,
            'error_type': error_type,
            'error_message': error_message,
            'context': kwargs.get('context', {}),
        })
        self._trim_error_log()
    
    def on_error(self, sender, error_type, error_message, task=None, **kwargs):
        """处理通用错误"""
        self.error_log.append({
            'timestamp': datetime.now(),
            'source': getattr(sender, '__class__', type(sender)).__name__,
            'error_type': error_type,
            'error_message': error_message,
            'task': task or {},
        })
        self._trim_error_log()
    
    def on_plugin_loaded(self, sender, plugin_name, capabilities=None, **kwargs):
        """处理插件加载事件"""
        self.capability_log.append({
            'timestamp': datetime.now(),
            'plugin': plugin_name,
            'capabilities': capabilities or {},
        })
    
    def _trim_error_log(self):
        """保持错误日志在合理大小"""
        if len(self.error_log) > 100:
            self.error_log = self.error_log[-100:]
    
    # =============================================================================
    # 报告接口
    # =============================================================================
    
    def get_field_demand_report(self) -> dict:
        """获取字段需求报告"""
        sorted_fields = sorted(
            self.field_demand_log.items(),
            key=lambda x: x[1]['count'],
            reverse=True
        )
        return {
            'total_unique_fields': len(sorted_fields),
            'top_missing_fields': [
                {'field': f, 'count': d['count'], 'symbols': list(d['symbols'])}
                for f, d in sorted_fields[:10]
            ],
            'all_demands': {
                f: {'count': d['count'], 'symbols': list(d['symbols'])}
                for f, d in sorted_fields
            }
        }
    
    def get_error_report(self) -> dict:
        """获取错误报告"""
        return {
            'total_errors': len(self.error_log),
            'by_source': self._count_by_source(),
            'recent_errors': self.error_log[-10:]
        }
    
    def _count_by_source(self) -> dict:
        """按来源统计错误"""
        counts = {}
        for err in self.error_log:
            source = err.get('source', 'unknown')
            counts[source] = counts.get(source, 0) + 1
        return counts
    
    # =============================================================================
    # Genes Spec
    # =============================================================================
    
    @property
    def commands(self) -> list[str]:
        return ["evo_report", "evo_field_demand", "evo_errors"]
    
    def handle(self, task: "Task") -> dict:
        """处理进化相关命令"""
        command = task.command
        
        if command == "evo_report":
            return {
                "success": True,
                "data": {
                    "field_demand": self.get_field_demand_report(),
                    "errors": self.get_error_report(),
                    "capabilities": self.capability_log,
                }
            }
        elif command == "evo_field_demand":
            return {"success": True, "data": self.get_field_demand_report()}
        elif command == "evo_errors":
            return {"success": True, "data": self.get_error_report()}
        
        return {"success": False, "error": f"Unknown command: {command}"}
```

## 5. 集成到 acorn-core

### 5.1 修改 kernel.py

```python
# acorn-core/src/acorn_core/kernel.py
from .events import EventBus

class Acorn:
    def __init__(self):
        self.pm = pluggy.PluginManager("evo")
        self.pm.add_hookspecs(Genes)
    
    def load_plugins(self):
        self.pm.load_setuptools_entrypoints("yapex.acorn.plugins")
        self.pm.hook.on_load()
        
        # 发送插件加载完成事件
        for plugin in self.pm.get_plugins():
            plugin_name = self._get_plugin_name(plugin)
            EventBus.emit(
                EventBus.PLUGIN_LOADED,
                sender=self,
                plugin_name=plugin_name,
                capabilities=getattr(plugin, 'get_capabilities', lambda: {})()
            )
    
    def execute(self, task: Task):
        handler = self._find_handler(task.command)
        if handler is None:
            return Response.err(
                code="NOT_IMPLEMENTED",
                message=f"No plugin handles command: {task.command}"
            )
        
        try:
            result = handler.handle(task)
            return self._format_response(result, handler)
        except Exception as e:
            # 发送错误事件
            EventBus.emit(
                EventBus.ERROR_OCCURRED,
                sender=handler,
                error_type=type(e).__name__,
                error_message=str(e),
                task={'command': task.command, 'args': task.args}
            )
            return Response.err(
                code="EXECUTION_ERROR",
                message=str(e)
            )
```

### 5.2 修改 evo_manager plugin.py

```python
# acorn-core/src/acorn_core/plugins/evo_manager.py
# 从 __init__.py 导入 EventBus
```

## 6. 使用示例

### 6.1 查询不存在的字段

```bash
# 用户请求不存在的字段
echo '{
  "command": "vi_query",
  "args": {"symbol": "600519", "fields": "custom_indicator"}
}' | nc -U ~/.acorn/agent.sock
```

**响应**：
```json
{
  "success": false,
  "error": "Fields not supported: custom_indicator"
}
```

**事件流程**：
```
用户请求 custom_indicator
    ↓
vi_core 检测到字段不存在
    ↓ emit(EventBus.FIELD_MISSING)
EventBus 广播事件
    ↓
evo_manager 记录: custom_indicator 请求次数 +1
    ↓
返回响应给用户
```

### 6.2 获取进化报告

```bash
# 查询进化管理器收集的数据
echo '{"command": "evo_report", "args": {}}' | nc -U ~/.acorn/agent.sock
```

**输出**：
```json
{
  "success": true,
  "data": {
    "field_demand": {
      "total_unique_fields": 5,
      "top_missing_fields": [
        {"field": "roic", "count": 10, "symbols": ["600519", "002027"]},
        {"field": "ev_ebitda", "count": 7, "symbols": ["600519"]}
      ]
    },
    "errors": {
      "total_errors": 3,
      "by_source": {"provider": 2, "calculator": 1},
      "recent_errors": [...]
    }
  }
}
```

## 7. 文件清单

| 文件 | 说明 |
|------|------|
| `acorn-core/src/acorn_core/events.py` | 事件总线实现 |
| `acorn-core/src/acorn_core/kernel.py` | 集成事件发送 |
| `acorn-core/src/acorn_core/plugins/evo_manager.py` | 事件订阅和学习 |
| `value-investment-plugin/vi_core/src/vi_core/plugin.py` | 业务事件发送 |

## 8. 依赖

```toml
# acorn-core/pyproject.toml
[project]
dependencies = [
    "pluggy>=1.6.0",
    "blinker>=1.7.0",
]
```

## 9. 演进路线

### Phase 1: 事件总线 ✅ (本文档)
- 实现 EventBus
- 业务层发送事件
- 进化层订阅并记录

### Phase 2: 能力发现
- 分析 field_demand_log
- 发现高频需求但缺失的字段
- 提示可开发新插件

### Phase 3: 错误学习
- 分析错误模式
- 提供修复建议
- 预防性提示

### Phase 4: 自我修复
- 根据历史错误自动调整
- 动态注册新能力
- 能力自动演进
