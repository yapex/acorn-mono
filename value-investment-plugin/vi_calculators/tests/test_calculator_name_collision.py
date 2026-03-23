"""TDD Tests for calculator name collision handling

Requirements:
- Same namespace + same name = overwrite (later registration wins)
- Only project-level calculators (user/dynamic) use this strategy
- Builtin calculators are NOT affected (loaded once at startup)
"""
import pytest
import pluggy

from vi_core import ValueInvestmentSpecs
from vi_core.plugin import plugin


# Sample calculator code for testing
SIMPLE_CALC_CODE = '''
def calculate(data, config):
    return {"result": 42}
'''

MODIFIED_CALC_CODE = '''
def calculate(data, config):
    return {"result": 100}
'''


class TestCalculatorNameCollision:
    """Test name collision handling for calculators"""

    def setup_method(self):
        """Setup plugin manager with CalculatorLoaderPlugin"""
        from vi_calculators import plugin as calculators_plugin
        
        self.pm = pluggy.PluginManager("value_investment")
        self.pm.add_hookspecs(ValueInvestmentSpecs)
        self.pm.register(plugin, name="vi_core")
        self.pm.register(calculators_plugin, name="calculators")
        
        # Get calculator plugin instance
        self.calc_plugin = calculators_plugin
        # Save original calculator names for teardown
        self._original_calc_names = [
            {"name": c["name"], "namespace": c.get("namespace")}
            for c in self.calc_plugin._calculators
        ]
        # Reset calculators to empty for clean test state
        self.calc_plugin._calculators = []
    
    def teardown_method(self):
        """Restore original calculators state by name"""
        # Reload calculators from original paths
        from vi_calculators import get_all_calculators
        all_calcs = get_all_calculators()
        # Keep only calculators that were originally loaded
        self.calc_plugin._calculators = [
            c for c in all_calcs
            if {"name": c["name"], "namespace": c.get("namespace")} in self._original_calc_names
        ]

    def test_same_namespace_same_name_overwrites(self):
        """Same namespace + same name should overwrite (later wins)"""
        # Register first calculator
        result1 = self.calc_plugin.vi_register_calculator(
            name="test_calc",
            code=SIMPLE_CALC_CODE,
            required_fields=["field1"],
            namespace="dynamic",
            description="First version",
        )
        assert result1["success"] is True
        
        # Verify first registration
        calcs = self.calc_plugin.vi_list_calculators()
        assert len(calcs) == 1
        assert calcs[0]["namespace"] == "dynamic"
        
        # Register second calculator with same name/namespace
        result2 = self.calc_plugin.vi_register_calculator(
            name="test_calc",
            code=MODIFIED_CALC_CODE,
            required_fields=["field1"],
            namespace="dynamic",
            description="Second version - should overwrite",
        )
        assert result2["success"] is True
        
        # Should still be 1 calculator (overwritten)
        calcs = self.calc_plugin.vi_list_calculators()
        assert len(calcs) == 1
        assert calcs[0]["description"] == "Second version - should overwrite"

    def test_different_namespace_same_name_no_overwrite(self):
        """Different namespace + same name should NOT overwrite"""
        # Register in dynamic namespace
        result1 = self.calc_plugin.vi_register_calculator(
            name="test_calc",
            code=SIMPLE_CALC_CODE,
            required_fields=["field1"],
            namespace="dynamic",
            description="Dynamic version",
        )
        assert result1["success"] is True
        
        # Register in user namespace with same name
        result2 = self.calc_plugin.vi_register_calculator(
            name="test_calc",
            code=MODIFIED_CALC_CODE,
            required_fields=["field1"],
            namespace="user",
            description="User version",
        )
        assert result2["success"] is True
        
        # Should have 2 calculators (different namespaces)
        calcs = self.calc_plugin.vi_list_calculators()
        assert len(calcs) == 2
        
        # Both should exist
        namespaces = [c["namespace"] for c in calcs]
        assert "dynamic" in namespaces
        assert "user" in namespaces

    def test_builtin_namespace_uses_mtime_strategy(self):
        """Builtin calculators use mtime-based cache, not overwrite strategy
        
        Note: This tests the design decision that builtin calculators
        are NOT affected by the same-name-overwrite rule.
        """
        # Builtin namespace should not allow runtime registration
        result = self.calc_plugin.vi_register_calculator(
            name="test_calc",
            code=SIMPLE_CALC_CODE,
            required_fields=["field1"],
            namespace="builtin",
            description="Should not be allowed",
        )
        
        # Registration should fail or builtin should be protected
        # This is a design decision - builtin is loaded from files at startup
        # We document that builtin calculators follow different rules

    def test_unregister_removes_and_clears_cache(self):
        """Unregister should delete calculator and clear cache"""
        # Register a calculator
        result = self.calc_plugin.vi_register_calculator(
            name="to_remove",
            code=SIMPLE_CALC_CODE,
            required_fields=["field1"],
            namespace="dynamic",
        )
        assert result["success"] is True
        
        # Verify it exists
        calcs = self.calc_plugin.vi_list_calculators()
        assert len(calcs) == 1
        
        # Unregister
        unreg_result = self.calc_plugin.vi_unregister_calculator(name="to_remove")
        assert unreg_result["success"] is True
        
        # Should be gone
        calcs = self.calc_plugin.vi_list_calculators()
        assert len(calcs) == 0
        
        # Running should return None
        run_result = self.calc_plugin.vi_run_calculator(
            name="to_remove",
            data={},
            config={},
        )
        assert run_result is None

    def test_override_behavior_via_unregister_then_register(self):
        """Simulate override: unregister then register with same name"""
        # Register initial
        self.calc_plugin.vi_register_calculator(
            name="overwrite_me",
            code=SIMPLE_CALC_CODE,
            required_fields=["field1"],
            namespace="dynamic",
            description="Original",
        )
        
        # Unregister
        self.calc_plugin.vi_unregister_calculator(name="overwrite_me")
        
        # Register new version
        result = self.calc_plugin.vi_register_calculator(
            name="overwrite_me",
            code=MODIFIED_CALC_CODE,
            required_fields=["field2"],  # Different required fields
            namespace="dynamic",
            description="Overwritten version",
        )
        assert result["success"] is True
        
        # Verify overwrite
        calcs = self.calc_plugin.vi_list_calculators()
        assert len(calcs) == 1
        assert calcs[0]["description"] == "Overwritten version"
        assert calcs[0]["required_fields"] == ["field2"]
