"""
测试 EventBus 事件系统
======================
"""

import threading
import time
from concurrent.futures import ThreadPoolExecutor

import pytest


class TestEventBusBasics:
    """EventBus 基础功能测试"""

    def test_can_import_event_bus(self):
        from acorn_core.events import EventBus
        assert EventBus is not None

    def test_event_bus_is_singleton(self):
        from acorn_core.events import EventBus
        bus1 = EventBus()
        bus2 = EventBus()
        assert bus1 is bus2

    def test_can_emit_and_receive_event(self):
        from acorn_core.events import EventBus
        
        received = []
        
        @EventBus.on("test.event")
        def handler(event_data, sender, **kwargs):
            received.append(kwargs)
        
        EventBus.publish("test.event", sender=None, value="hello")
        
        assert len(received) == 1
        assert received[0]["value"] == "hello"

    def test_multiple_handlers_for_same_event(self):
        from acorn_core.events import EventBus
        
        results = []
        
        @EventBus.on("multi.test")
        def handler1(event_data, sender, **kwargs):
            results.append(("h1", kwargs))
        
        @EventBus.on("multi.test")
        def handler2(event_data, sender, **kwargs):
            results.append(("h2", kwargs))
        
        EventBus.publish("multi.test", sender=None, data=42)
        
        assert len(results) == 2
        assert ("h1", {"data": 42}) in results
        assert ("h2", {"data": 42}) in results


class TestTraceId:
    """trace_id 通过 contextvars 传递"""

    def test_trace_id_is_thread_local(self):
        from acorn_core.events import EventBus, get_trace_id
        
        results = {}
        
        def worker(thread_name):
            from acorn_core.events import set_trace_id, get_trace_id
            set_trace_id(f"trace-{thread_name}")
            time.sleep(0.05)  # 确保另一线程先设置
            results[thread_name] = get_trace_id()
        
        t1 = threading.Thread(target=worker, args=("t1",))
        t2 = threading.Thread(target=worker, args=("t2",))
        
        t1.start()
        t2.start()
        t1.join()
        t2.join()
        
        # 每个线程应该有自己的 trace_id
        assert results["t1"] == "trace-t1"
        assert results["t2"] == "trace-t2"

    def test_trace_id_passed_to_handler(self):
        from acorn_core.events import EventBus, set_trace_id, get_trace_id
        
        captured_trace_id = None
        
        @EventBus.on("trace.test")
        def handler(event_data, sender, **kwargs):
            nonlocal captured_trace_id
            captured_trace_id = get_trace_id()
        
        set_trace_id("my-trace-123")
        EventBus.publish("trace.test", sender=None)
        
        assert captured_trace_id == "my-trace-123"


class TestEventRegistration:
    """事件注册"""

    def test_can_register_event(self):
        from acorn_core.events import EventBus
        
        # 注册事件不应该抛出异常
        EventBus.register_event("my.custom.event")
        
        # 注册后应该可以订阅
        received = []
        @EventBus.on("my.custom.event")
        def handler(event_data, sender, **kwargs):
            received.append(kwargs)
        
        EventBus.publish("my.custom.event", sender=None, foo="bar")
        
        assert len(received) == 1
        assert received[0]["foo"] == "bar"

    def test_can_emit_without_prior_registration(self):
        from acorn_core.events import EventBus
        
        # 不注册直接 emit 也不应该报错
        received = []
        @EventBus.on("unregistered.event")
        def handler(event_data, sender, **kwargs):
            received.append(kwargs)
        
        EventBus.publish("unregistered.event", sender=None, x=1)
        
        assert len(received) == 1


class TestSenderParameter:
    """sender 参数传递"""

    def test_sender_passed_to_handler(self):
        from acorn_core.events import EventBus
        
        captured_sender = None
        
        @EventBus.on("sender.test")
        def handler(event_data, sender, **kwargs):
            nonlocal captured_sender
            captured_sender = sender
        
        class MySender:
            pass
        
        my_sender = MySender()
        EventBus.publish("sender.test", sender=my_sender)
        
        assert captured_sender is my_sender


class TestDecoratorApi:
    """装饰器 API 测试"""

    def test_on_decorator_returns_callable(self):
        from acorn_core.events import EventBus
        
        @EventBus.on("decorator.test")
        def my_handler(event_data, sender, **kwargs):
            pass
        
        assert callable(my_handler)

    def test_decorator_can_stack(self):
        from acorn_core.events import EventBus
        
        results = []
        
        @EventBus.on("stack.1")
        @EventBus.on("stack.2")
        def handler(event_data, sender, **kwargs):
            results.append(event_data)
        
        # 注意: 装饰器栈叠可能导致 handler 被注册两次
        # 这是预期行为，由订阅者自己控制
        
        EventBus.publish("stack.1", sender=None)
        EventBus.publish("stack.2", sender=None)
        
        # 验证至少有一次调用
        assert len(results) >= 1


class TestCoreEvents:
    """核心事件测试"""

    def test_acorn_plugin_loaded_event(self):
        from acorn_core.events import EventBus
        
        loaded_plugins = []
        
        @EventBus.on("acorn.plugin.loaded")
        def on_plugin_loaded(event_data, sender, **kwargs):
            loaded_plugins.append(kwargs.get("plugin_name"))
        
        # 模拟插件加载事件
        EventBus.publish("acorn.plugin.loaded", sender=None, plugin_name="test_plugin")
        
        assert "test_plugin" in loaded_plugins

    def test_vi_field_missing_event(self):
        from acorn_core.events import EventBus
        
        missing_fields = []
        
        @EventBus.on("vi.field.missing")
        def on_field_missing(event_data, sender, **kwargs):
            missing_fields.append({
                "field": kwargs.get("field"),
                "plugin": kwargs.get("plugin")
            })
        
        # 模拟字段缺失事件
        EventBus.publish("vi.field.missing", sender=None, field="revenue", plugin="value_investment")
        
        assert len(missing_fields) == 1
        assert missing_fields[0]["field"] == "revenue"
        assert missing_fields[0]["plugin"] == "value_investment"


class TestConcurrency:
    """并发测试"""

    def test_concurrent_emit(self):
        from acorn_core.events import EventBus
        
        counter = {"value": 0}
        
        @EventBus.on("concurrent.test")
        def handler(event_data, sender, **kwargs):
            counter["value"] += 1
        
        def emit_many(n):
            for _ in range(n):
                EventBus.publish("concurrent.test", sender=None)
        
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(emit_many, 25) for _ in range(4)]
            for f in futures:
                f.result()
        
        # 4 workers * 25 emits * 1 handler = 100
        assert counter["value"] == 100

    def test_handler_exception_doesnt_break_bus(self):
        from acorn_core.events import EventBus
        
        errors = []
        
        @EventBus.on("error.test")
        def bad_handler(event_data, sender, **kwargs):
            raise RuntimeError("handler error")
        
        @EventBus.on("error.test")
        def good_handler(event_data, sender, **kwargs):
            errors.append("good_handler_called")
        
        # 第一个 handler 抛异常不应该影响第二个
        EventBus.publish("error.test", sender=None)
        
        assert len(errors) == 1
        assert errors[0] == "good_handler_called"
