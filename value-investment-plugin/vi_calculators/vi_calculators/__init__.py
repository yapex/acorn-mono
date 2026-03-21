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

命名空间策略：
    - builtin: value-investment-plugin/calculators（可信）
    - user: ~/.value_investment/calculators（用户定义）
    - dynamic: 运行时动态注册（第三方，未验证）
"""
from __future__ import annotations

import importlib.util
import os
import types
import uuid
from pathlib import Path
from typing import Any

from vi_core.spec import vi_hookimpl, CalculatorSpec  # type: ignore[import]


# 默认加载路径
DEFAULT_CALC_PATHS = {
    "builtin": Path(__file__).parent.parent.parent / "calculators",  # value-investment-plugin/calculators
    "user": Path.home() / ".value_investment" / "calculators",
}


def load_calculators_from_path(path: Path, namespace: str) -> list[dict]:
    """从目录加载所有 calculator 脚本

    Args:
        path: 计算器目录路径
        namespace: 命名空间标签（builtin/user/dynamic）

    Returns:
        计算器列表，每个 dict 包含 name, module, required_fields, description, namespace
    """
    calculators = []

    if not path.exists() or not path.is_dir():
        return calculators

    for file in sorted(path.glob("calc_*.py")):
        if file.name.startswith("_"):
            continue

        try:
            # 使用 namespace 前缀避免冲突
            module_name = f"vi_calc.{namespace}.{file.stem}"
            spec = importlib.util.spec_from_file_location(module_name, file)
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
                    "namespace": namespace,
                })
        except Exception:
            pass

    return calculators


def get_all_calculators() -> list[dict]:
    """从所有配置路径加载计算器"""
    calculators = []
    seen = set()

    for namespace, path in DEFAULT_CALC_PATHS.items():
        for calc in load_calculators_from_path(path, namespace):
            if calc["name"] not in seen:
                calculators.append(calc)
                seen.add(calc["name"])

    return calculators


def create_isolated_module(namespace: str, name: str) -> types.ModuleType:
    """创建一个隔离的模块命名空间

    Args:
        namespace: 命名空间标签（dynamic/user/builtin）
        name: 计算器名称

    Returns:
        隔离的 module 对象
    """
    module = types.ModuleType(f"vi_calc.{namespace}.{name}")
    # 不注册到 sys.modules，保持隔离
    return module


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
                "namespace": c.get("namespace", "unknown"),
            }
            for c in self._calculators
        ]

    @vi_hookimpl
    def vi_run_calculator(
        self,
        name: str,
        data: dict[str, dict[int, Any]],
        config: dict[str, Any],
    ) -> dict[str, Any] | None:
        """执行指定名称的计算器"""
        for calc in self._calculators:
            if calc["name"] == name:
                try:
                    result = calc["module"].calculate(data, config)
                    return result
                except Exception as e:
                    # 返回错误信息而不是抛出异常
                    error_type = type(e).__name__
                    error_msg = str(e)
                    return {
                        "__error__": True,
                        "calculator": name,
                        "namespace": calc.get("namespace", "unknown"),
                        "error_type": error_type,
                        "error_message": error_msg,
                    }
        return None

    @vi_hookimpl
    def vi_register_calculator(
        self,
        name: str,
        code: str,
        required_fields: list[str],
        namespace: str,
        description: str = "",
    ) -> dict[str, Any]:
        """运行时注册新计算器（通过代码字符串）

        Args:
            name: 计算器名称
            code: Python 代码，包含 calculate(results, config) 函数
            required_fields: 所需字段列表
            description: 描述
            namespace: 命名空间标签，默认 dynamic（第三方）
                         可选: builtin, user, dynamic
        """
        try:
            # 为动态计算器创建隔离的模块命名空间
            unique_id = uuid.uuid4().hex[:8]
            module = create_isolated_module(namespace, f"{name}_{unique_id}")

            # 在隔离命名空间中执行代码
            exec(code, module.__dict__)

            if not hasattr(module, "calculate"):
                return {
                    "success": False,
                    "error": {"code": "INVALID_CODE", "message": "Missing 'calculate' function in code"},
                }

            # 包装为类实例（保持接口一致）
            calc_fn = module.calculate

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
                "namespace": namespace,
                "module_id": unique_id,
            })

            return {
                "success": True,
                "data": {
                    "name": name,
                    "namespace": namespace,
                    "required_fields": required_fields,
                    "total_calculators": len(self._calculators),
                },
            }

        except SyntaxError as e:
            return {
                "success": False,
                "error": {
                    "code": "SYNTAX_ERROR",
                    "message": f"Syntax error in code: {e.filename}:{e.lineno} - {e.msg}"
                },
            }
        except Exception as e:
            return {
                "success": False,
                "error": {"code": "REGISTRATION_FAILED", "message": str(e)},
            }


# Pluggy 插件实例
plugin = CalculatorLoaderPlugin()
