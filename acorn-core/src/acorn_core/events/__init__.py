"""
Acorn Core Events - 事件系统代理包
==================================
将 EventBus 委托给 acorn_events 共享包。
"""

from acorn_events import EventBus, get_trace_id, set_trace_id

__all__ = ["EventBus", "get_trace_id", "set_trace_id"]
