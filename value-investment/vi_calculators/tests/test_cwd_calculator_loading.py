"""Test loading calculators from an arbitrary working directory.

Scenario:
- Create a temp directory with a calculators/ subfolder
- Put a calc_*.py file in it
- Verify get_all_calculators() picks it up when cwd is that temp directory
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest


TEST_CALC_CODE = '''\
"""Test calculator from cwd"""
REQUIRED_FIELDS = ["total_assets", "total_revenue"]
SUPPORTED_MARKETS = ["HK"]

def calculate(data):
    import pandas as pd
    return data["total_revenue"] / data["total_assets"].replace(0, float('nan'))
'''


class TestCwdCalculatorLoading:
    """Test that calculators are loaded from the current working directory."""

    def test_cwd_calculator_is_loaded(self):
        """Calculators in <cwd>/calculators/ should be discoverable."""
        with tempfile.TemporaryDirectory() as tmpdir:
            calc_dir = Path(tmpdir) / "calculators"
            calc_dir.mkdir()
            (calc_dir / "calc_cwd_test.py").write_text(TEST_CALC_CODE, encoding="utf-8")

            # Simulate loading from that cwd
            from vi_calculators import load_calculators_from_path

            calcs = load_calculators_from_path(calc_dir, namespace="cwd")

            assert len(calcs) == 1
            assert calcs[0]["name"] == "cwd_test"
            assert calcs[0]["namespace"] == "cwd"
            assert calcs[0]["supported_markets"] == ["HK"]
            assert "total_assets" in calcs[0]["required_fields"]

    def test_get_all_calculators_includes_cwd(self):
        """get_all_calculators() should include calculators from cwd."""
        with tempfile.TemporaryDirectory() as tmpdir:
            calc_dir = Path(tmpdir) / "calculators"
            calc_dir.mkdir()
            (calc_dir / "calc_cwd_test.py").write_text(TEST_CALC_CODE, encoding="utf-8")

            # Save original cwd and switch
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                from vi_calculators import get_all_calculators

                all_calcs = get_all_calculators()
                names = [c["name"] for c in all_calcs]
                assert "cwd_test" in names
            finally:
                os.chdir(original_cwd)

    def test_cwd_calc_overrides_builtin(self):
        """A cwd calculator with the same name should override builtin."""
        with tempfile.TemporaryDirectory() as tmpdir:
            calc_dir = Path(tmpdir) / "calculators"
            calc_dir.mkdir()
            # Use same name as an existing builtin calculator
            (calc_dir / "calc_npcf_ratio.py").write_text(TEST_CALC_CODE, encoding="utf-8")

            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                from vi_calculators import get_all_calculators

                all_calcs = get_all_calculators()
                # Find the npcf_ratio entry
                matches = [c for c in all_calcs if c["name"] == "npcf_ratio"]
                assert len(matches) == 1
                assert matches[0]["namespace"] == "cwd"
                assert matches[0]["supported_markets"] == ["HK"]
            finally:
                os.chdir(original_cwd)

    def test_non_calc_files_are_ignored(self):
        """Files not starting with calc_ should be ignored."""
        with tempfile.TemporaryDirectory() as tmpdir:
            calc_dir = Path(tmpdir) / "calculators"
            calc_dir.mkdir()
            (calc_dir / "helper.py").write_text("# not a calculator\n", encoding="utf-8")
            (calc_dir / "_calc_hidden.py").write_text("# hidden\n", encoding="utf-8")
            (calc_dir / "calc_valid.py").write_text(TEST_CALC_CODE, encoding="utf-8")

            from vi_calculators import load_calculators_from_path

            calcs = load_calculators_from_path(calc_dir, namespace="cwd")
            assert len(calcs) == 1
            assert calcs[0]["name"] == "valid"

    def test_cwd_without_calculators_dir(self):
        """If <cwd>/calculators/ does not exist, no cwd calculators are loaded."""
        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                from vi_calculators import get_all_calculators

                all_calcs = get_all_calculators()
                cwd_calcs = [c for c in all_calcs if c["namespace"] == "cwd"]
                assert len(cwd_calcs) == 0
            finally:
                os.chdir(original_cwd)

    def test_cwd_calculator_can_run(self):
        """A cwd-loaded calculator should produce correct results."""
        with tempfile.TemporaryDirectory() as tmpdir:
            calc_dir = Path(tmpdir) / "calculators"
            calc_dir.mkdir()
            (calc_dir / "calc_cwd_test.py").write_text(TEST_CALC_CODE, encoding="utf-8")

            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)

                # Build plugin manager and register
                import pluggy
                from vi_core import ValueInvestmentSpecs
                from vi_core.plugin import plugin as core_plugin
                from vi_calculators import CalculatorEngine

                pm = pluggy.PluginManager("value_investment")
                pm.add_hookspecs(ValueInvestmentSpecs)
                pm.register(core_plugin, name="vi_core")

                # Create a fresh CalculatorEngine (it calls get_all_calculators internally)
                engine = CalculatorEngine()
                pm.register(engine, name="calculators")

                # Run the calculator
                import pandas as pd
                data = {
                    "total_assets": pd.Series([1000, 2000], index=[2023, 2024]),
                    "total_revenue": pd.Series([500, 1000], index=[2023, 2024]),
                }
                result = pm.hook.vi_run_calculator(
                    name="cwd_test", data=data, config={}, market_code="HK"
                )
                # pluggy returns [result]
                series = result[0] if isinstance(result, list) else result
                assert series is not None
                assert series.iloc[0] == 0.5  # 500/1000
                assert series.iloc[1] == 0.5  # 1000/2000

            finally:
                os.chdir(original_cwd)
