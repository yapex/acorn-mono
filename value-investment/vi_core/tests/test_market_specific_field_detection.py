"""Test market-specific field detection logic

验证港股查询时，字段检测逻辑只考虑港股 Provider 的字段，
而不被 A 股 Provider 的字段"掩盖"。
"""
import pytest
from unittest.mock import MagicMock, patch

from vi_core.plugin import ViCorePlugin


class TestMarketSpecificFieldDetection:
    """测试按市场过滤 Provider 字段"""

    def test_infer_market_hk(self):
        """测试港股代码推断"""
        plugin = ViCorePlugin()
        assert plugin._infer_market("00700") == "HK"
        assert plugin._infer_market("09988") == "HK"
        assert plugin._infer_market("00001") == "HK"

    def test_infer_market_a(self):
        """测试 A 股代码推断"""
        plugin = ViCorePlugin()
        assert plugin._infer_market("600519") == "A"
        assert plugin._infer_market("000001") == "A"
        assert plugin._infer_market("300750") == "A"

    def test_infer_market_us(self):
        """测试美股代码推断"""
        plugin = ViCorePlugin()
        assert plugin._infer_market("AAPL") == "US"
        assert plugin._infer_market("TSLA") == "US"

    def test_get_provider_fields_for_market(self):
        """测试按市场获取 Provider 字段"""
        plugin = ViCorePlugin()

        # Mock plugin manager
        mock_pm = MagicMock()

        # 模拟两个 Provider：A 股和港股
        # A 股 Provider 支持 total_shares
        # 港股 Provider 不支持 total_shares
        a_provider = MagicMock()
        a_provider.vi_markets.return_value = ["A"]
        a_provider.vi_supported_fields.return_value = ["total_shares", "market_cap"]

        hk_provider = MagicMock()
        hk_provider.vi_markets.return_value = ["HK"]
        hk_provider.vi_supported_fields.return_value = ["market_cap", "pe_ratio"]

        mock_pm.get_plugins.return_value = [a_provider, hk_provider]

        # 调用 _get_provider_fields_for_market
        with patch.object(plugin, '_get_plugin_manager', return_value=mock_pm):
            # 港股查询应该只返回港股 Provider 的字段
            hk_fields = plugin._get_provider_fields_for_market("HK")
            assert "market_cap" in hk_fields
            assert "pe_ratio" in hk_fields
            assert "total_shares" not in hk_fields  # 关键：港股不支持

            # A 股查询应该只返回 A 股 Provider 的字段
            a_fields = plugin._get_provider_fields_for_market("A")
            assert "total_shares" in a_fields
            assert "market_cap" in a_fields
            assert "pe_ratio" not in a_fields  # A 股 Provider 没有 pe_ratio

    def test_hk_query_triggers_capability_missing(self):
        """测试港股查询缺失字段时触发 EVO_CAPABILITY_MISSING 事件"""
        plugin = ViCorePlugin()

        # Mock event bus
        mock_event_bus = MagicMock()
        plugin._event_bus = mock_event_bus

        # Mock plugin manager
        mock_pm = MagicMock()

        # 模拟 vi_fields hook - 返回所有标准字段
        mock_pm.hook.vi_fields.return_value = [
            {"source": "core", "fields": {"total_shares": {"description": "总股本"}}}
        ]

        # 模拟 vi_list_calculators hook
        mock_pm.hook.vi_list_calculators.return_value = []

        # 模拟 vi_provide_items hook - 返回空数据
        mock_pm.hook.vi_provide_items.return_value = []

        # 模拟 vi_markets 和 vi_supported_fields
        # A 股 Provider 支持 total_shares
        # 港股 Provider 不支持 total_shares
        mock_pm.hook.vi_markets.return_value = [["A"], ["HK"]]
        mock_pm.hook.vi_supported_fields.return_value = [
            ["total_shares", "market_cap"],  # A 股 Provider
            ["market_cap", "pe_ratio"]       # 港股 Provider
        ]

        with patch.object(plugin, '_get_plugin_manager', return_value=mock_pm):
            # 查询港股 00700 的 total_shares
            result = plugin._query({
                "symbol": "00700",
                "items": "total_shares",
                "years": 1
            })

            # 验证事件被触发
            mock_event_bus.publish.assert_called_once()
            call_args = mock_event_bus.publish.call_args

            # 验证事件类型
            assert call_args[0][0] == "evo.capability.missing"

            # 验证事件内容包含 total_shares
            context = call_args[1]["context"]
            assert "total_shares" in context.get("unfilled", []) or \
                   "total_shares" in context.get("unsupported", [])


class TestProviderFieldFiltering:
    """测试 Provider 字段过滤逻辑"""

    def test_provider_markets_mapping(self):
        """测试 Provider 市场映射关系"""
        plugin = ViCorePlugin()

        mock_pm = MagicMock()

        # 模拟多个 Provider
        provider_a = MagicMock()
        provider_a.vi_markets.return_value = ["A"]
        provider_a.vi_supported_fields.return_value = ["roe", "roa"]

        provider_hk = MagicMock()
        provider_hk.vi_markets.return_value = ["HK"]
        provider_hk.vi_supported_fields.return_value = ["roe", "market_cap"]

        provider_multi = MagicMock()
        provider_multi.vi_markets.return_value = ["A", "HK"]
        provider_multi.vi_supported_fields.return_value = ["pe_ratio"]

        mock_pm.get_plugins.return_value = [provider_a, provider_hk, provider_multi]

        with patch.object(plugin, '_get_plugin_manager', return_value=mock_pm):
            # A 股市场：应该包含 A 股 Provider 和多市场 Provider
            a_fields = plugin._get_provider_fields_for_market("A")
            assert "roe" in a_fields
            assert "roa" in a_fields
            assert "pe_ratio" in a_fields  # 多市场 Provider
            assert "market_cap" not in a_fields  # 仅港股 Provider

            # 港股市场：应该包含港股 Provider 和多市场 Provider
            hk_fields = plugin._get_provider_fields_for_market("HK")
            assert "roe" in hk_fields
            assert "market_cap" in hk_fields
            assert "pe_ratio" in hk_fields  # 多市场 Provider
            assert "roa" not in hk_fields  # 仅 A 股 Provider


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
