"""Calculator Loader Plugin

从配置的路径自动发现并加载 calculator 脚本。

目录结构示例：
    calculators/
        calc_implied_growth.py
        calc_peg.py
        calc_xxx.py

calculator 脚本格式：
    REQUIRED_FIELDS = ["field_a", "field_b"]

    def calculate(data, config):
        # data: {field: {year: value}}
        # config: 用户配置
        return {"result_field": value}
"""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path
from typing import Any

from vi_core.spec import vi_hookimpl, CalculatorSpec  # type: ignore[import]


# 默认加载路径
DEFAULT_CALC_PATHS = [
    Path(__file__).parent.parent.parent / "calculators",  # value-investment-plugin/calculators
    Path.home() / ".value_investment" / "calculators",
]


def load_calculators_from_path(path: Path) -> list[dict]:
    """从目录加载所有 calculator 脚本"""
    calculators = []
    
    if not path.exists() or not path.is_dir():
        return calculators
    
    for file in sorted(path.glob("calc_*.py")):
        if file.name.startswith("_"):
            continue
        
        try:
            spec = importlib.util.spec_from_file_location(file.stem, file)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                # 检查必需的属性
                if not hasattr(module, "calculate"):
                    continue
                
                required_fields = getattr(module, "REQUIRED_FIELDS", [])
                description = getattr(module, "__doc__", "") or ""
                name = file.stem.replace("calc_", "")
                
                calculators.append({
                    "name": name,
                    "module": module,
                    "required_fields": required_fields,
                    "description": description.strip().split("\n")[0],
                })
        except Exception:
            pass
    
    return calculators


def get_all_calculators() -> list[dict]:
    """从所有配置路径加载计算器"""
    calculators = []
    seen = set()
    
    for path in DEFAULT_CALC_PATHS:
        for calc in load_calculators_from_path(path):
            if calc["name"] not in seen:
                calculators.append(calc)
                seen.add(calc["name"])
    
    return calculators


class CalculatorLoaderPlugin(CalculatorSpec):
    """Calculator 加载器插件"""

    def __init__(self):
        self._calculators = get_all_calculators()

    @vi_hookimpl
    def vi_list_calculators(self) -> list[dict[str, Any]]:
        """返回所有已加载的计算器"""
        return [
            {
                "name": c["name"],
                "required_fields": c["required_fields"],
                "description": c["description"],
            }
            for c in self._calculators
        ]

    @vi_hookimpl
    def vi_run_calculator(
        self,
        name: str,
        data: dict[str, dict[int, Any]],
        config: dict[str, Any],
    ) -> Any | None:
        """执行指定名称的计算器"""
        for calc in self._calculators:
            if calc["name"] == name:
                return calc["module"].calculate(data, config)
        return None

    @vi_hookimpl
    def vi_register_calculator(
        self,
        name: str,
        code: str,
        required_fields: list[str],
        description: str = "",
    ) -> dict[str, Any]:
        """运行时注册新计算器（通过代码字符串）"""
        try:
            namespace = {}
            exec(code, namespace)

            if "calculate" not in namespace:
                return {
                    "success": False,
                    "error": {"code": "INVALID_CODE", "message": "Missing 'calculate' function in code"},
                }

            # 创建动态模块（calculate 作为实例方法）
            calc_fn = namespace["calculate"]

            class DynamicCalculator:
                REQUIRED_FIELDS = required_fields
                __doc__ = description

                def calculate(self, results, config):
                    return calc_fn(results, config)

            dynamic_module = DynamicCalculator()

            self._calculators.append({
                "name": name,
                "module": dynamic_module,
                "required_fields": required_fields,
                "description": description,
            })

            return {
                "success": True,
                "data": {
                    "name": name,
                    "required_fields": required_fields,
                    "total_calculators": len(self._calculators),
                },
            }

        except Exception as e:
            return {
                "success": False,
                "error": {"code": "REGISTRATION_FAILED", "message": str(e)},
            }


# Pluggy 插件实例
plugin = CalculatorLoaderPlugin()
