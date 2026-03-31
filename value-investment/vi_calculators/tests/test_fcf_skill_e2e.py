"""End-to-end test: FCF skill calculator loaded from cwd.

Simulates the real deployment scenario:
- A skill's calculators/ directory exists under cwd
- acorn-agent starts with cwd pointing to that directory
- get_all_calculators() should discover and load them
- The calculator should produce correct results
"""
from __future__ import annotations

import os
from pathlib import Path

import pluggy
import pytest

# Skill source directory (value-investment/skills/acorn-vi-fcf/calculators)
SKILL_CALC_DIR = Path(__file__).resolve().parent.parent.parent / "skills" / "acorn-vi-fcf" / "calculators"


class TestFcfSkillE2E:
    """End-to-end test for FCF skill calculator loading and execution."""

    def test_fcf_calculator_discovered_from_cwd(self):
        """Simulate acorn-agent starting with cwd = skill root directory."""
        skill_root = SKILL_CALC_DIR.parent
        original_cwd = os.getcwd()

        try:
            os.chdir(skill_root)
            from vi_calculators import get_all_calculators

            all_calcs = get_all_calculators()
            names = [c["name"] for c in all_calcs]
            assert "free_cash_flow" in names, f"free_cash_flow not found in {names}"
        finally:
            os.chdir(original_cwd)

    def test_free_cash_flow_calculation(self):
        """calc_free_cash_flow should compute OCF - CAPEX correctly."""
        original_cwd = os.getcwd()
        skill_root = SKILL_CALC_DIR.parent

        try:
            os.chdir(skill_root)

            from vi_calculators import CalculatorEngine
            from vi_core import ValueInvestmentSpecs
            from vi_core.plugin import plugin as core_plugin

            pm = pluggy.PluginManager("value_investment")
            pm.add_hookspecs(ValueInvestmentSpecs)
            pm.register(core_plugin, name="vi_core")

            engine = CalculatorEngine()
            pm.register(engine, name="calculators")

            import pandas as pd
            data = {
                "operating_cash_flow": pd.Series([500, 600, 400], index=[2022, 2023, 2024]),
                "capital_expenditure": pd.Series([100, 150, 80], index=[2022, 2023, 2024]),
            }
            result = pm.hook.vi_run_calculator(
                name="free_cash_flow", data=data, config={}, market_code="HK"
            )
            series = result[0] if isinstance(result, list) else result

            assert series is not None
            assert series.iloc[0] == 400  # 500-100
            assert series.iloc[1] == 450  # 600-150
            assert series.iloc[2] == 320  # 400-80

        finally:
            os.chdir(original_cwd)

    def test_market_codes_are_correct(self):
        """Verify market codes match expectations."""
        original_cwd = os.getcwd()
        skill_root = SKILL_CALC_DIR.parent

        try:
            os.chdir(skill_root)
            from vi_calculators import get_all_calculators

            all_calcs = get_all_calculators()
            fcf = next(c for c in all_calcs if c["name"] == "free_cash_flow")
            assert fcf["market_codes"] == ["HK", "US"]

        finally:
            os.chdir(original_cwd)

    def test_market_filtering(self):
        """Calculator should only run for HK and US, not A."""
        original_cwd = os.getcwd()
        skill_root = SKILL_CALC_DIR.parent

        try:
            os.chdir(skill_root)

            from vi_calculators import CalculatorEngine
            from vi_core import ValueInvestmentSpecs
            from vi_core.plugin import plugin as core_plugin

            pm = pluggy.PluginManager("value_investment")
            pm.add_hookspecs(ValueInvestmentSpecs)
            pm.register(core_plugin, name="vi_core")

            engine = CalculatorEngine()
            pm.register(engine, name="calculators")

            import pandas as pd
            data = {
                "operating_cash_flow": pd.Series([500, 600], index=[2023, 2024]),
                "capital_expenditure": pd.Series([100, 150], index=[2023, 2024]),
            }

            # A market should return empty (not supported)
            result_a = pm.hook.vi_run_calculator(
                name="free_cash_flow", data=data, config={}, market_code="A"
            )
            series_a = result_a[0] if isinstance(result_a, list) else result_a
            assert series_a.empty

            # HK market should return results
            result_hk = pm.hook.vi_run_calculator(
                name="free_cash_flow", data=data, config={}, market_code="HK"
            )
            series_hk = result_hk[0] if isinstance(result_hk, list) else result_hk
            assert not series_hk.empty
            assert series_hk.iloc[0] == 400

        finally:
            os.chdir(original_cwd)
