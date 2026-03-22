"""
Context Variables for Trace ID
===============================
使用 contextvars 实现线程本地的 trace_id 传递。
"""

from contextvars import ContextVar

# trace_id 的 context variable
_trace_id_var: ContextVar[str] = ContextVar("trace_id", default="")


def get_trace_id() -> str:
    """获取当前 trace_id"""
    return _trace_id_var.get()


def set_trace_id(trace_id: str) -> None:
    """设置当前 trace_id"""
    _trace_id_var.set(trace_id)
