#!/usr/bin/env python3
"""
检查 pluggy hookspec 是否有默认值参数。

pluggy 1.6.0+ 将有默认值的参数归类为 kwargnames，
在 hook dispatch 时静默丢弃（impl 收到的是默认值而非调用方传入的值）。

规则：所有 @vi_hookspec 装饰的方法，其参数（self 除外）不应有默认值。
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path


def check_file(filepath: Path) -> list[str]:
    """检查一个 Python 文件中的 hookspec 默认值问题"""
    issues: list[str] = []

    source = filepath.read_text(encoding="utf-8")
    tree = ast.parse(source)

    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue

        # 检查装饰器是否包含 "hookspec"
        has_hookspec = False
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Call):
                func = decorator.func
                name = ""
                if isinstance(func, ast.Attribute):
                    name = func.attr
                elif isinstance(func, ast.Name):
                    name = func.id
                if "hookspec" in name.lower():
                    has_hookspec = True
                    break
            elif isinstance(decorator, ast.Name):
                if "hookspec" in decorator.id.lower():
                    has_hookspec = True
                    break

        if not has_hookspec:
            continue

        args = node.args
        all_params = args.args + args.kwonlyargs  # 不含 self
        all_params = [a for a in all_params if a.arg != "self"]

        # defaults 对应 all_params 尾部的参数
        # kw_defaults 对应 kwonly_args
        n_defaults = len(args.defaults)
        n_kwonly = len(args.kwonlyargs)

        # Positional args with defaults: 最后 n_defaults 个 positional args（不含 self）
        positional_params = args.args[1:]  # skip self
        params_with_defaults = positional_params[-n_defaults:] if n_defaults else []

        for arg in params_with_defaults:
            issues.append(
                f"{filepath}:{node.lineno}: {node.name}() param '{arg.arg}' has default value "
                f"(pluggy will silently drop this on dispatch)"
            )

        # Kwonly args with non-None defaults
        for i, default in enumerate(args.kw_defaults):
            if default is not None:
                issues.append(
                    f"{filepath}:{node.lineno}: {node.name}() kwonly param '{args.kwonlyargs[i].arg}' "
                    f"has default value (pluggy will silently drop this on dispatch)"
                )

    return issues


def main() -> int:
    target_files = sys.argv[1:] if len(sys.argv) > 1 else []

    if not target_files:
        root = Path(__file__).parent.parent
        spec_files = list(root.glob("*/src/*/spec.py"))
        if not spec_files:
            print("No spec.py found")
            return 1
        target_files = [str(f) for f in spec_files]

    all_issues: list[str] = []
    for filepath in target_files:
        all_issues.extend(check_file(Path(filepath)))

    if all_issues:
        print("❌ hookspec 参数默认值问题（pluggy 1.6.0+ 会静默丢弃 kwargnames）:")
        for issue in all_issues:
            print(f"  {issue}")
        print(f"\n共 {len(all_issues)} 个问题")
        print("规则：@vi_hookspec 方法的所有参数不应有默认值")
        return 1
    else:
        print("✅ 所有 hookspec 参数无默认值")
        return 0


if __name__ == "__main__":
    sys.exit(main())
