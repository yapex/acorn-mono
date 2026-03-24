"""
TDD: Calculator 扩展请求事件测试

场景：
1. 用户请求计算 debt_to_ebitda
2. Calculator 不存在
3. ViCorePlugin 遍历插件查找进化规范
4. Evolution Manager 通过 Hook 提供进化规范
"""

import pytest
import pandas as pd
from unittest.mock import MagicMock, patch


class TestCalculatorExtensionEvent:
    """Calculator 扩展请求事件测试"""

    def test_calculator_not_found_publishes_event(self):
        """
        当请求的计算器不存在时，应该发布 EVO_CAPABILITY_MISSING 事件
        """
        # 模拟 EventBus
        mock_event_bus = MagicMock()

        # 创建真实的 DataFrame
        df = pd.DataFrame({
            "fiscal_year": [2020, 2021, 2022],
            "interest_bearing_debt": [100, 120, 140],
            "ebitda": [50, 60, 70],
        })
        df = df.set_index("fiscal_year")

        # 导入被测模块
        from vi_core.plugin import ViCorePlugin
        from acorn_events import AcornEvents

        # 创建插件实例，注入 mock EventBus
        plugin = ViCorePlugin(event_bus=mock_event_bus)

        # Mock plugin manager - 设置类属性（因为 _get_plugin_manager 是类方法）
        mock_pm = MagicMock()
        mock_pm.hook.vi_list_calculators.return_value = [[]]  # 空列表
        ViCorePlugin._pm = mock_pm

        # 调用 _run_calculators
        result = plugin._run_calculators(
            df=df,
            calculator_names={"debt_to_ebitda"},
            calculator_config={}
        )

        # 验证 EventBus.publish 被调用
        assert mock_event_bus.publish.called, "EventBus.publish 应该被调用"

        # 验证事件类型
        call_args = mock_event_bus.publish.call_args
        assert call_args[0][0] == AcornEvents.EVO_CAPABILITY_MISSING, \
            f"期望事件类型 'EVO_CAPABILITY_MISSING', 得到 '{call_args[0][0]}'"

        # 验证事件数据包含 capability_type
        kwargs = call_args[1]
        assert kwargs.get("capability_type") == "calculator", \
            f"期望 capability_type='calculator', 得到 '{kwargs.get('capability_type')}'"

        # 验证事件数据包含 name
        assert kwargs.get("name") == "debt_to_ebitda", \
            f"期望 name='debt_to_ebitda', 得到 '{kwargs.get('name')}'"

        # 清理
        ViCorePlugin._pm = None


class TestEvoManager:
    """Evolution Manager 处理能力缺失事件测试"""

    def test_evo_manager_subscribes_to_capability_missing_event(self):
        """
        Evolution Manager 应该订阅 EVO_CAPABILITY_MISSING 事件
        """
        from acorn_core.plugins.evo_manager import EvoManager
        from acorn_events import AcornEvents

        mock_event_bus = MagicMock()
        mock_pm = MagicMock()  # 不使用 spec，因为 pluggy.PluginManager 没有 hook 属性
        evo = EvoManager(pm=mock_pm, event_bus=mock_event_bus)
        evo.on_load()  # 触发订阅

        # 验证订阅了 EVO_CAPABILITY_MISSING
        calls = mock_event_bus.on.call_args_list
        event_types = [call[0][0] for call in calls]
        assert AcornEvents.EVO_CAPABILITY_MISSING in event_types, \
            f"EvoManager 应该订阅 EVO_CAPABILITY_MISSING, 得到 {event_types}"

    def test_evo_manager_records_capability_missing(self):
        """
        Evolution Manager 收到 EVO_CAPABILITY_MISSING 事件后，
        应该记录 capability_missing
        """
        from acorn_core.plugins.evo_manager import EvoManager
        from acorn_events import AcornEvents

        mock_pm = MagicMock()
        evo = EvoManager(pm=mock_pm, event_bus=None)
        evo.on_load()

        # 直接调用事件处理器
        evo._on_capability_missing(
            event_type=AcornEvents.EVO_CAPABILITY_MISSING,
            sender="ViCorePlugin",
            capability_type="calculator",
            name="debt_to_ebitda",
            context={"symbol": "600519"}
        )

        # 验证 EvoManager 记录了能力缺失
        assert len(evo.capability_missing) > 0, "应该记录 capability_missing"
        req = evo.capability_missing[0]
        assert req["capability_type"] == "calculator"
        assert req["name"] == "debt_to_ebitda"
        assert req["context"]["symbol"] == "600519"

    def test_get_evolution_spec_calls_plugin_method(self):
        """
        _get_evolution_spec 方法应该从插件中获取进化规范
        """
        from acorn_core.plugins.evo_manager import EvoManager

        # 创建 mock pm - 插件实现了 get_evolution_spec 方法
        mock_plugin = MagicMock()
        mock_plugin.get_evolution_spec.return_value = "进化规范..."

        mock_pm = MagicMock()
        mock_pm.get_plugins.return_value = [mock_plugin]

        evo = EvoManager(pm=mock_pm, event_bus=None)

        # 调用 _get_evolution_spec
        result = evo._get_evolution_spec(
            capability_type="calculator",
            name="debt_to_ebitda",
            context={"symbol": "600519"}
        )

        # 验证调用了插件的 get_evolution_spec 方法
        mock_plugin.get_evolution_spec.assert_called_once_with(
            "calculator",
            "debt_to_ebitda",
            {"symbol": "600519"}
        )
        assert result == "进化规范..."


class TestFindEvolutionSpec:
    """测试 ViCorePlugin._find_evolution_spec 方法"""

    def test_find_evolution_spec_from_plugin(self):
        """
        _find_evolution_spec 应该从插件中获取进化规范
        """
        from vi_core.plugin import ViCorePlugin

        plugin = ViCorePlugin()

        # Mock plugin manager - 创建一个有 get_evolution_spec 方法的插件
        mock_plugin = MagicMock()
        mock_plugin.get_evolution_spec.return_value = "进化规范..."

        mock_pm = MagicMock()
        mock_pm.get_plugins.return_value = [mock_plugin]
        ViCorePlugin._pm = mock_pm  # 设置类属性

        # 调用 _find_evolution_spec
        result = plugin._find_evolution_spec(
            capability_type="calculator",
            name="debt_to_ebitda",
            context={"symbol": "600519"}
        )

        # 验证返回了进化规范
        assert result == "进化规范..."
        mock_plugin.get_evolution_spec.assert_called_once_with(
            "calculator", "debt_to_ebitda", {"symbol": "600519"}
        )

        # 清理
        ViCorePlugin._pm = None

    def test_find_evolution_spec_returns_none_when_no_plugin_provides(self):
        """
        当没有插件提供进化规范时，应该返回 None
        """
        from vi_core.plugin import ViCorePlugin

        plugin = ViCorePlugin()

        # Mock plugin manager - 插件没有 get_evolution_spec 方法
        mock_plugin_without_spec = MagicMock(spec=[])  # 空 spec，没有 get_evolution_spec

        mock_pm = MagicMock()
        mock_pm.get_plugins.return_value = [mock_plugin_without_spec]
        ViCorePlugin._pm = mock_pm  # 设置类属性

        # 调用 _find_evolution_spec
        result = plugin._find_evolution_spec(
            capability_type="calculator",
            name="unknown_calculator",
            context=None
        )

        # 验证返回 None
        assert result is None

        # 清理
        ViCorePlugin._pm = None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
