"""
沙箱工具
========
安全执行 Calculator 代码的简单工具。
"""

from __future__ import annotations

from typing import Any

try:
    from RestrictedPython import compile_restricted
    from RestrictedPython.Guards import safe_builtins
    HAS_RESTRICTED_PYTHON = True
except ImportError:
    HAS_RESTRICTED_PYTHON = False


def execute_sandbox(code: str, allowed_modules: dict[str, Any] | None = None) -> dict[str, Any]:
    """
    在沙箱中安全执行代码

    Args:
        code: Python 代码字符串
        allowed_modules: 允许的模块，如 {"pd": pandas}

    Returns:
        执行后的局部命名空间

    Raises:
        SyntaxError: 代码包含危险操作（eval/exec/import）
        RuntimeError: 执行出错或 RestrictedPython 未安装

    Example:
        >>> import pandas as pd
        >>> code = '''
        ... def calculate(data, config):
        ...     return data["a"] + data["b"]
        ... '''
        >>> result = execute_sandbox(code, {"pd": pd})
        >>> result["calculate"]({"a": 1, "b": 2}, {})
        3
    """
    if not HAS_RESTRICTED_PYTHON:
        raise RuntimeError("RestrictedPython not installed. Run: pip install RestrictedPython")

    # 1. 编译（编译期安全检查）
    try:
        bytecode = compile_restricted(code, '<sandbox>', 'exec')
    except SyntaxError as e:
        raise SyntaxError(f"Dangerous code detected: {e}")

    # 2. 构建受限环境
    restricted_globals = {
        "__builtins__": safe_builtins,
        "_getattr_": getattr,
        "_getitem_": _safe_getitem,
        "_getiter_": lambda obj: iter(obj),
        "_write_": lambda obj: obj,
    }

    # 添加允许的模块
    if allowed_modules:
        restricted_globals.update(allowed_modules)

    # 3. 执行
    local_vars = {}
    exec(bytecode, restricted_globals, local_vars)

    return local_vars


def _safe_getitem(obj: Any, key: Any) -> Any:
    """
    安全的 getitem，阻止访问 __xxx__ 属性
    """
    if isinstance(key, str) and key.startswith('_'):
        raise KeyError(f"Access to '{key}' is not allowed")
    return obj[key]


def validate_calculator_code(code: str, test_data: dict, allowed_modules: dict[str, Any] | None = None) -> dict[str, Any]:
    """
    验证 Calculator 代码

    在沙箱中执行代码，并调用 calculate 函数进行测试。

    Args:
        code: Calculator 代码字符串
        test_data: 测试数据 {"data": {...}, "config": {...}}
        allowed_modules: 允许的模块

    Returns:
        {"success": True, "result": ...} 或 {"success": False, "error": ...}
    """
    try:
        # 1. 执行代码
        local_vars = execute_sandbox(code, allowed_modules)

        # 2. 检查 calculate 函数
        if "calculate" not in local_vars:
            return {"success": False, "error": "Missing calculate function"}

        # 3. 检查 REQUIRED_FIELDS
        if "REQUIRED_FIELDS" not in local_vars:
            return {"success": False, "error": "Missing REQUIRED_FIELDS"}

        # 4. 运行测试
        result = local_vars["calculate"](test_data["data"], test_data.get("config", {}))

        return {"success": True, "result": result}

    except SyntaxError as e:
        return {"success": False, "error": f"Syntax error: {e}"}
    except KeyError as e:
        return {"success": False, "error": f"Key error: {e}"}
    except Exception as e:
        return {"success": False, "error": f"Runtime error: {e}"}
