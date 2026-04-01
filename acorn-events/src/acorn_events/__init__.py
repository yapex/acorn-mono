"""
Acorn EventBus - 事件发布-订阅系统
==================================
使用 blinker 实现的简单事件总线。

主要接口：
- publish(event_type, sender, **data): 发布事件
- on(event_type): 装饰器订阅事件
- register_event(event_type): 注册事件类型

事件常量：
- AcornEvents: 系统事件类型常量
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable

from blinker import signal  # type: ignore[import]

from .context import get_trace_id, set_trace_id

if TYPE_CHECKING:
    from blinker import Signal


# =============================================================================
# 系统事件常量
# =============================================================================

class AcornEvents:
    """
    Acorn 核心系统事件常量
    
    所有系统事件都应使用这些常量定义，避免硬编码字符串。
    订阅方可以直接导入使用：
    
    Example:
        from acorn_events import EventBus, AcornEvents
        
        bus.publish(AcornEvents.EVO_CAPABILITY_MISSING, sender=self, capability_type="calculator", name="xxx")
        bus.on(AcornEvents.SYS_PLUGIN_LOADED)(self._on_plugin_loaded)
    
    命名规范：
    - `sys.*` - 系统生命周期事件（核心框架）
    - `evo.*` - 演化相关事件（核心框架）
    
    注意：
    - 业务领域事件（如 vi.*）由各业务插件自行定义
    - 核心框架不依赖任何业务概念
    """

    # ─────────────────────────────────────────────────────────────────────
    # 系统生命周期事件 (sys.*)
    # ─────────────────────────────────────────────────────────────────────

    #: 系统启动完成
    SYS_STARTUP = "sys.startup"

    #: 系统关闭
    SYS_SHUTDOWN = "sys.shutdown"

    # ─────────────────────────────────────────────────────────────────────
    # 插件生命周期事件 (sys.*)
    # ─────────────────────────────────────────────────────────────────────

    #: 插件加载完成
    SYS_PLUGIN_LOADED = "sys.plugin.loaded"

    #: 插件卸载
    SYS_PLUGIN_UNLOADED = "sys.plugin.unloaded"

    # ─────────────────────────────────────────────────────────────────────
    # 演化相关事件 (evo.*)
    # ─────────────────────────────────────────────────────────────────────

    #: 能力缺失（核心能力不足，需要进化）
    #: 由业务插件发布，sender 标识能力缺失的模块
    #: payload: capability_type, name, context
    EVO_CAPABILITY_MISSING = "evo.capability.missing"

    #: 进化请求（Evolution Manager 开始处理）
    EVO_REQUEST = "evo.request"

    #: 进化开始（发送规范给 LLM）
    EVO_START = "evo.start"

    #: 进化成功（LLM 完成部署）
    EVO_SUCCESS = "evo.success"

    #: 进化失败（LLM 交互或部署失败）
    EVO_FAILED = "evo.failed"

    #: 进化冲突（多个插件响应同一能力）
    EVO_CONFLICT = "evo.conflict"

    #: 进化已入队
    EVO_QUEUED = "evo.queued"

    #: 固化完成（进化结果持久化）
    EVO_COMMITTED = "evo.committed"


class EventBus:
    """
    单例事件总线
    
    使用 blinker 作为底层实现，提供:
    - publish(event_type, sender, **data): 发布事件
    - on(event_type): 装饰器订阅事件
    - register_event(event_type): 注册事件类型
    """

    _instance: EventBus | None = None
    _initialized: bool = False

    def __new__(cls) -> EventBus:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._wrapped_handlers = []
        return cls._instance

    def __init__(self) -> None:
        if EventBus._initialized:
            return
        EventBus._initialized = True
        self._signals: dict[str, Signal] = {}
        self._wrapped_handlers: list[Callable[..., Any]] = []  # 保持 strong reference 防止 GC

    def __call__(self) -> EventBus:
        """允许 EventBus() 返回单例实例"""
        return self

    def publish(self, event_type: str, sender: Any, **data: Any) -> None:
        """
        发布事件
        
        Args:
            event_type: 事件类型
            sender: 发布者对象
            **data: 事件数据
        """
        s = self._signals.get(event_type)
        if s is None:
            s = signal(event_type)
            self._signals[event_type] = s

        # 传递 trace_id 给接收者
        data["_trace_id"] = get_trace_id()
        s.send(sender, **data)

    def _wrap_handler(self, event_type: str, handler: Callable[..., Any]) -> Callable[..., Any]:
        """
        包装 handler，使其符合 blinker 签名 (sender, **kwargs)
        但内部调用时传递 (event_type, sender, **kwargs)
        """
        def wrapped(sender: Any, **kwargs: Any) -> None:
            try:
                # 恢复 trace_id 到 context
                trace_id = kwargs.pop("_trace_id", "")
                if trace_id:
                    set_trace_id(trace_id)
                return handler(event_type, sender, **kwargs)
            except Exception:
                # 吞下异常，不影响其他 handler
                pass

        # 保持 strong reference 防止 GC (blinker 使用弱引用)
        self._wrapped_handlers.append(wrapped)
        return wrapped

    def on(self, event_type: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """
        事件订阅装饰器
        
        Args:
            event_type: 事件类型
            
        Returns:
            装饰器函数
        """
        def decorator(handler: Callable[..., Any]) -> Callable[..., Any]:
            s = self._signals.get(event_type)
            if s is None:
                s = signal(event_type)
                self._signals[event_type] = s

            # 包装 handler 以匹配 blinker 签名
            wrapped = self._wrap_handler(event_type, handler)
            s.connect(wrapped)
            return handler
        return decorator

    def register_event(self, event_type: str) -> None:
        """
        注册事件类型
        
        Args:
            event_type: 事件类型
        """
        if event_type not in self._signals:
            self._signals[event_type] = signal(event_type)


# 全局单例实例
EventBus = EventBus()  # type: ignore[assignment, misc]  # noqa: N816

__all__ = ["EventBus", "AcornEvents", "EvolutionSpec", "get_trace_id", "set_trace_id"]


# =============================================================================
# Evolution Hook 接口
# =============================================================================

class EvolutionSpec:
    """
    进化机制 Hook 接口 - 框架级通用协议
    
    当系统发现能力缺失时，通过此 Hook 询问所有插件：
    "你能提供这个能力的进化规范吗？"
    
    使用方式：
    1. 在具体的 PluginManager 中使用对应的 hookspec 装饰器添加此接口
       例如：
       - acorn_core: 使用 hookspec("evo")
       - vi_core: 使用 vi_hookspec("value_investment")
    
    Example:
        # vi_core/spec.py
        from acorn_events import EvolutionSpec
        from pluggy import HookspecMarker
        
        vi_hookspec = HookspecMarker("value_investment")
        
        class EvolutionSpecHook(EvolutionSpec):
            @vi_hookspec(firstresult=True)
            def get_evolution_spec(self, capability_type: str, name: str, context: dict | None = None) -> str | None:
                ...
    """

    def get_evolution_spec(
        self,
        capability_type: str,
        name: str,
        context: dict | None = None,
    ) -> str | None:
        """
        询问插件是否支持某能力，不支持则返回进化规范
        
        Args:
            capability_type: 能力类型，如 "calculator", "field", "command" 等
            name: 具体名称，如 "npcf_ratio"
            context: 可选的上下文信息，如 {"symbol": "600519"}
        
        Returns:
            None - 支持此能力或不关心此类型
            str  - 不支持，返回进化规范（给 LLM 的 prompt）
        
        示例返回值:
            '''要创建计算器 `npcf_ratio`，请按以下格式提供代码：

            ```python
            REQUIRED_FIELDS = ["operating_cash_flow", "net_profit"]

            def calculate(data, config):
                return data["operating_cash_flow"] / data["net_profit"]
            ```
            '''
        """
        return None
