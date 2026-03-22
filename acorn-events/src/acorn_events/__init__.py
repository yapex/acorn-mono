"""
Acorn EventBus - 事件发布-订阅系统
==================================
使用 blinker 实现的简单事件总线。

主要接口：
- publish(event_type, sender, **data): 发布事件
- on(event_type): 装饰器订阅事件
- register_event(event_type): 注册事件类型
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable

from blinker import signal  # type: ignore[import]

from .context import get_trace_id, set_trace_id

if TYPE_CHECKING:
    from blinker import Signal


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
