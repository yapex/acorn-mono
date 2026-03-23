"""
TDD: Calculator 扩展请求事件测试

场景：
1. 用户请求计算 debt_to_ebitda
2. Calculator 不存在
3. EventBus 发布 calculator.extension_needed 事件
4. Evolution Manager 收到事件，返回 extension_prompt
"""

import pytest
import pandas as pd
from unittest.mock import MagicMock, patch


class TestCalculatorExtensionEvent:
    """Calculator 扩展请求事件测试"""

    def test_calculator_not_found_publishes_event(self):
        """
        当请求的计算器不存在时，应该发布 calculator.extension_needed 事件

        期望：
        - EventBus.publish 被调用，事件类型为 "calculator.extension_needed"
        - 事件包含 calculator_name, extension_prompt
        """
        # 模拟 EventBus
        mock_event_bus = MagicMock()

        # 创建真实的 DataFrame（不是 mock）
        df = pd.DataFrame({
            "fiscal_year": [2020, 2021, 2022],
            "interest_bearing_debt": [100, 120, 140],
            "ebitda": [50, 60, 70],
        })
        df = df.set_index("fiscal_year")

        # 导入被测模块
        from vi_core.plugin import ViCorePlugin

        # 创建插件实例，注入 mock EventBus
        plugin = ViCorePlugin(event_bus=mock_event_bus)

        # Mock plugin manager 返回空的 calculator 列表
        mock_pm = MagicMock()
        mock_pm.hook.vi_list_calculators.return_value = [[]]  # 空列表
        ViCorePlugin._pm = mock_pm

        # 调用 _run_calculators，请求不存在的计算器
        result = plugin._run_calculators(
            df=df,
            calculator_names={"debt_to_ebitda"},
            calculator_config={}
        )

        # 验证 EventBus.publish 被调用
        assert mock_event_bus.publish.called, "EventBus.publish 应该被调用"

        # 验证事件类型
        call_args = mock_event_bus.publish.call_args
        assert call_args[0][0] == "calculator.extension_needed", \
            f"期望事件类型 'calculator.extension_needed', 得到 '{call_args[0][0]}'"

        # 验证事件数据包含 calculator_name
        kwargs = call_args[1]
        assert kwargs.get("calculator_name") == "debt_to_ebitda", \
            f"期望 calculator_name='debt_to_ebitda', 得到 '{kwargs.get('calculator_name')}'"

        # 验证事件数据包含 extension_prompt
        assert "extension_prompt" in kwargs, "事件应包含 extension_prompt"
        prompt = kwargs["extension_prompt"]
        assert "debt_to_ebitda" in prompt, "extension_prompt 应包含 calculator_name"


class TestEvoManagerCalculatorExtension:
    """Evolution Manager 处理 Calculator 扩展请求测试"""

    def test_evo_manager_subscribes_to_calculator_extension_event(self):
        """
        Evolution Manager 应该订阅 calculator.extension_needed 事件
        """
        from acorn_core.plugins.evo_manager import EvoManager
        from unittest.mock import MagicMock

        mock_event_bus = MagicMock()
        evo = EvoManager(event_bus=mock_event_bus)
        evo.on_load()  # 触发订阅

        # 验证订阅了 calculator.extension_needed
        calls = mock_event_bus.on.call_args_list
        event_types = [call[0][0] for call in calls]
        assert "calculator.extension_needed" in event_types, \
            f"EvoManager 应该订阅 calculator.extension_needed, 得到 {event_types}"

    def test_evo_manager_records_extension_request(self):
        """
        Evolution Manager 收到 calculator.extension_needed 事件后，
        应该记录 extension_request
        """
        from acorn_core.plugins.evo_manager import EvoManager

        evo = EvoManager(event_bus=None)
        evo.on_load()

        # 直接调用事件处理器
        evo._on_calculator_extension_needed(
            event_type="calculator.extension_needed",
            sender=self,
            calculator_name="debt_to_ebitda",
            extension_prompt="这是扩展提示...",
            symbol="600519"
        )

        # 验证 EvoManager 记录了扩展请求
        assert len(evo.extension_requests) > 0, "应该记录 extension_request"
        req = evo.extension_requests[0]
        assert req["calculator_name"] == "debt_to_ebitda"
        assert "extension_prompt" in req


if __name__ == "__main__":
    pytest.main([__file__, "-v"])