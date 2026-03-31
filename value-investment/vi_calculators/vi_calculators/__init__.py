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

import pandas as pd
from typing import Any

import pluggy  # type: ignore[import]

vi_hookimpl = pluggy.HookimplMarker("value_investment")


# 默认加载路径
# editable 模式: vi_calculators/vi_calculators/__init__.py -> ../../../calculators
# wheel 模式: site-packages/vi_calculators/__init__.py -> ../calculators (force-include)
_editable_calc_path = Path(__file__).parent.parent.parent / "calculators"
_wheel_calc_path = Path(__file__).parent.parent / "calculators"

DEFAULT_CALC_PATHS = {
    "builtin": _editable_calc_path if _editable_calc_path.exists() else _wheel_calc_path,
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
                field_aliases = getattr(module, "FIELD_ALIASES", {})
                supported_markets = getattr(module, "SUPPORTED_MARKETS", ["A", "HK", "US"])
                description = getattr(module, "__doc__", "") or ""
                name = file.stem.replace("calc_", "")

                calculators.append({
                    "name": name,
                    "module": module,
                    "required_fields": required_fields,
                    "field_aliases": field_aliases,
                    "supported_markets": supported_markets,
                    "description": description.strip().split("\n")[0],
                    "namespace": namespace,
                })
        except Exception:
            pass

    return calculators


def get_all_calculators() -> list[dict]:
    """从所有配置路径加载计算器
    
    加载顺序：
    1. builtin: 可信的内置计算器 (value-investment-plugin/calculators/)
    2. cwd: 当前工作目录下的 calculators/ (用户临时创建的)
    3. user: 用户目录下的计算器 (~/.value_investment/calculators/)
    
    注意：后面的会覆盖前面的同名计算器
    """
    calculators = []
    seen = set()

    # 动态添加 cwd 路径
    calc_paths = dict(DEFAULT_CALC_PATHS)
    cwd_calc_path = Path.cwd() / "calculators"
    if cwd_calc_path.exists() and cwd_calc_path.is_dir():
        calc_paths["cwd"] = cwd_calc_path

    for namespace, path in calc_paths.items():
        for calc in load_calculators_from_path(path, namespace):
            if calc["name"] in seen:
                # 同名覆盖：移除旧版本，用新版本替代
                calculators = [c for c in calculators if c["name"] != calc["name"]]
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


class CalculatorEngine:
    """
    Calculator 引擎
    
    职责：
    - 发现和加载计算器
    - 运行计算器
    - 提供进化规范
    """

    def __init__(self):
        self._calculators = get_all_calculators()

    @vi_hookimpl
    def vi_list_calculators(self) -> list[dict[str, Any]]:
        """返回所有已加载的计算器"""
        return [
            {
                "name": c["name"],
                "required_fields": c["required_fields"],
                "field_aliases": c.get("field_aliases", {}),
                "supported_markets": c.get("supported_markets", ["A", "HK", "US"]),
                "description": c["description"],
                "namespace": c.get("namespace", "unknown"),
            }
            for c in self._calculators
        ]

    @vi_hookimpl
    def get_evolution_spec(
        self,
        capability_type: str,
        name: str,
        context: dict | None,
    ) -> str | None:
        """
        询问是否支持某计算器，如果不支持，返回进化规范
        
        Args:
            capability_type: 能力类型（如 "calculator"）
            name: 计算器名称
            context: 上下文信息
            
        Returns:
            None - 支持此计算器或不关心此类型
            str - 不支持，返回进化规范（给 LLM 的 prompt）
        """
        # 不关心非 calculator 类型
        if capability_type != "calculator":
            return None
        
        # 检查是否已支持
        for calc in self._calculators:
            if calc["name"] == name:
                return None
        
        # 不支持，返回进化规范
        # 提示 Agent 读取 skill 文件，不要硬编码路径
        skill_name = "acorn-vi-calculator-creation"
        return f'''要创建计算器 `{name}`，请读取 skill `{skill_name}` 获取完整的创建指南。

如果系统中未安装该 skill，请报错："Calculator creation skill not found: {skill_name}"
'''

    def _run_in_sandbox(self, calc: dict, data: dict[str, pd.Series]) -> pd.Series | dict:
        """在沙箱中运行 Calculator"""
        from .sandbox import execute_sandbox

        # 获取源代码
        code = calc.get("_source_code")
        if not code:
            # 内置 calculator 没有保存源代码，需要反编译（简化处理：直接运行）
            try:
                result = calc["module"].calculate(data)
                return result
            except Exception as e:
                return {
                    "__error__": True,
                    "calculator": calc["name"],
                    "namespace": calc.get("namespace", "unknown"),
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                }

        # 动态 calculator：在沙箱中执行
        try:
            local_vars = execute_sandbox(code, {"pd": pd})
            if "calculate" not in local_vars:
                return {
                    "__error__": True,
                    "calculator": calc["name"],
                    "error": "Missing calculate function",
                }

            result = local_vars["calculate"](data)
            return result

        except Exception as e:
            return {
                "__error__": True,
                "calculator": calc["name"],
                "namespace": calc.get("namespace", "unknown"),
                "error_type": type(e).__name__,
                "error_message": str(e),
            }

    @vi_hookimpl
    def vi_run_calculator(
        self,
        name: str,
        data: dict[str, pd.Series],
        config: dict[str, Any],
        market_code: str | None,
    ) -> pd.Series | None:
        """执行指定名称的计算器
        
        Args:
            name: 计算器名称
            data: {字段名: pd.Series} 格式的数据
            market_code: 市场代码，用于市场兼容性检查
            
        Returns:
            pd.Series 计算结果，或 None（市场不兼容时返回空 Series）
        """
        for calc in self._calculators:
            if calc["name"] == name:
                # 检查市场兼容性
                supported_markets = calc.get("supported_markets", ["A", "HK", "US"])
                if market_code and market_code not in supported_markets:
                    # 市场不兼容，返回空 Series
                    return pd.Series(dtype=float)
                
                result = self._run_in_sandbox(calc, data)
                return result

        # 懒加载：在当前工作目录下的 calculators/ 中查找
        cwd_calc_path = Path.cwd() / "calculators"
        if cwd_calc_path.exists() and cwd_calc_path.is_dir():
            found = load_calculators_from_path(cwd_calc_path, "cwd")
            calc = next((c for c in found if c["name"] == name), None)
            if calc:
                # 缓存起来，下次直接用
                self._calculators.append(calc)
                supported_markets = calc.get("supported_markets", ["A", "HK", "US"])
                if market_code and market_code not in supported_markets:
                    return pd.Series(dtype=float)
                return self._run_in_sandbox(calc, data)

        return None

    @vi_hookimpl
    def vi_register_calculator(
        self,
        name: str,
        code: str,
        required_fields: list[str],
        namespace: str,
        description: str,
        supported_markets: list[str] | None = None,
    ) -> dict[str, Any]:
        """运行时注册新计算器（通过代码字符串）

        代码在运行时会统一在沙箱中执行，注册时无需验证。

        Args:
            name: 计算器名称
            code: Python 代码，包含 calculate(results, config) 函数
            required_fields: 所需字段列表
            description: 描述
            namespace: 命名空间标签，默认 dynamic（第三方）
                         可选: builtin, user, dynamic
            supported_markets: 支持的市场代码列表，默认 None 表示支持所有市场
        """
        try:
            # 2. 为动态计算器创建隔离的模块命名空间
            unique_id = uuid.uuid4().hex[:8]
            module = create_isolated_module(namespace, f"{name}_{unique_id}")

            # 3. 在隔离命名空间中执行代码
            exec(code, module.__dict__)

            if not hasattr(module, "calculate"):
                return {
                    "success": False,
                    "error": {"code": "INVALID_CODE", "message": "Missing 'calculate' function in code"},
                }

            # 4. 包装为类实例（保持接口一致）
            calc_fn = module.calculate

            class DynamicCalculator:
                REQUIRED_FIELDS = required_fields
                SUPPORTED_MARKETS = supported_markets or ["A", "HK", "US"]
                __doc__ = description

                def calculate(self, data):
                    return calc_fn(data)

            dynamic_module = DynamicCalculator()

            # 5. 保存源代码用于 reload
            # 先移除同 namespace 同名的旧 calculator（overwrite 策略）
            self._calculators = [
                c for c in self._calculators
                if not (c["name"] == name and c.get("namespace") == namespace)
            ]

            self._calculators.append({
                "name": name,
                "module": dynamic_module,
                "required_fields": required_fields,
                "supported_markets": supported_markets or ["A", "HK", "US"],
                "description": description,
                "namespace": namespace,
                "module_id": unique_id,
                "_source_code": code,  # 保存源代码
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

    def _find_calculator(self, name: str) -> dict | None:
        """查找计算器"""
        for calc in self._calculators:
            if calc["name"] == name:
                return calc
        return None

    @vi_hookimpl
    def vi_unregister_calculator(
        self,
        name: str,
    ) -> dict[str, Any]:
        """卸载计算器

        Args:
            name: 计算器名称

        Returns:
            {"success": True} 或 {"success": False, "error": ...}
        """
        calc = self._find_calculator(name)
        if not calc:
            return {
                "success": False,
                "error": {"code": "NOT_FOUND", "message": f"Calculator '{name}' not found"},
            }

        # 从列表中移除
        self._calculators.remove(calc)

        # 清理模块引用（帮助垃圾回收）
        calc["module"] = None

        return {
            "success": True,
            "data": {"name": name, "total_calculators": len(self._calculators)},
        }

    @vi_hookimpl
    def vi_reload_calculator(
        self,
        name: str | None = None,
        code: str | None = None,
        required_fields: list[str] | None = None,
        description: str | None = None,
    ) -> dict[str, Any]:
        """重新加载计算器

        name 为 None 时：重新扫描所有预定目录，加载新增/修改的文件计算器，保留动态计算器。
        name 指定时：仅从文件系统重新加载指定计算器。

        Args:
            name: 计算器名称（None 表示全部重新扫描）
            code: 新代码（可选，仅 name 指定时有效）
            required_fields: 新字段列表（可选）
            description: 新描述（可选）

        Returns:
            {"success": True, "data": {}} 或 {"success": False, "error": ...}
        """
        # 保留动态计算器（运行时通过代码字符串注册的）
        dynamic_calcs = [c for c in self._calculators if c.get("_source_code")]

        if name is None:
            # 全量重新扫描所有预定目录
            file_calcs = get_all_calculators()
            self._calculators = file_calcs + dynamic_calcs

            return {
                "success": True,
                "data": {
                    "total": len(self._calculators),
                    "file_based": len(file_calcs),
                    "dynamic": len(dynamic_calcs),
                },
            }

        # 指定名称：重新扫描文件系统，找到目标计算器
        file_calcs = get_all_calculators()
        found = next((c for c in file_calcs if c["name"] == name), None)

        if not found:
            # 文件里没有，检查动态计算器
            dyn_found = next((c for c in dynamic_calcs if c["name"] == name), None)
            if dyn_found:
                if code is not None:
                    dyn_found["_source_code"] = code
                if required_fields is not None:
                    dyn_found["required_fields"] = required_fields
                if description is not None:
                    dyn_found["description"] = description
                return {
                    "success": True,
                    "data": {"name": name, "source": "dynamic_updated"},
                }
            return {
                "success": False,
                "error": {"code": "NOT_FOUND", "message": f"Calculator '{name}' not found"},
            }

        # 如果传了新代码，按动态方式覆盖文件版本
        if code is not None:
            self._calculators = file_calcs + dynamic_calcs
            return self.vi_register_calculator(
                name=name,
                code=code,
                required_fields=required_fields or found["required_fields"],
                description=description or found["description"],
                namespace=found.get("namespace", "builtin"),
            )

        # 用文件系统的最新版本替换内存中的旧版本
        self._calculators = file_calcs + dynamic_calcs
        return {
            "success": True,
            "data": {"name": name, "source": "file_rescanned"},
        }


# Pluggy 插件实例
plugin = CalculatorEngine()
