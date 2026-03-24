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
    Acorn 系统事件常量
    
    所有系统事件都应使用这些常量定义，避免硬编码字符串。
    订阅方可以直接导入使用：
    
    Example:
        from acorn_events import EventBus, AcornEvents
        
        bus.on(AcornEvents.FIELD_UNSUPPORTED)(self._on_field_unsupported)
        
        bus.publish(AcornEvents.CALCULATOR_EXTENSION_NEEDED, sender=self, calculator_name="xxx")
    """
    
    # ─────────────────────────────────────────────────────────────────────
    # 字段相关事件
    # ─────────────────────────────────────────────────────────────────────
    
    #: 系统不支持某字段（字段不在标准字段定义中）
    FIELD_UNSUPPORTED = "vi.field.unsupported"
    
    #: 字段无法填充（字段在标准中但 Provider 不支持或返回空）
    FIELD_UNFILLED = "vi.field.unfilled"
    
    # ─────────────────────────────────────────────────────────────────────
    # 计算器相关事件
    # ─────────────────────────────────────────────────────────────────────
    
    #: 需要扩展计算器（请求的计算器不存在）
    CALCULATOR_EXTENSION_NEEDED = "calculator.extension_needed"
    
    #: 计算器已注册
    CALCULATOR_REGISTERED = "calculator.registered"
    
    # ─────────────────────────────────────────────────────────────────────
    # 系统生命周期事件
    # ─────────────────────────────────────────────────────────────────────
    
    #: 系统启动完成
    SYSTEM_STARTUP = "system.startup"
    
    #: 系统关闭
    SYSTEM_SHUTDOWN = "system.shutdown"
    
    # ─────────────────────────────────────────────────────────────────────
    # 插件生命周期事件
    # ─────────────────────────────────────────────────────────────────────
    
    #: 插件加载完成
    PLUGIN_LOADED = "acorn.plugin.loaded"
    
    #: 插件卸载
    PLUGIN_UNLOADED = "acorn.plugin.unloaded"


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

__all__ = ["EventBus", "AcornEvents", "get_trace_id", "set_trace_id"]
