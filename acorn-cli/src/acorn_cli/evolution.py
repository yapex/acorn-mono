"""
Evolution System - Calculator 创建场景
=====================================

通过 CLI 接口与 LLM Agent 交互，创建财务指标计算器。

场景：创建新的财务指标计算器（如 debt_to_ebitda）
"""

from __future__ import annotations

import sys


# =============================================================================
# 当前能力：已有计算器列表
# =============================================================================

AVAILABLE_CALCULATORS = {
    "implied_growth": {"description": "隐含增长率", "required_fields": ["operating_cash_flow", "market_cap"]},
    "roe": {"description": "净资产收益率", "required_fields": ["net_profit", "total_equity"]},
    "roa": {"description": "资产回报率", "required_fields": ["net_profit", "total_assets"]},
}


def check_calculator(field_name: str) -> dict | None:
    """检查计算器是否存在"""
    return AVAILABLE_CALCULATORS.get(field_name)


# =============================================================================
# Evolution 模式
# =============================================================================

def evolution_mode(
    intent: str | None = None,
    field_name: str | None = None,
    formula: str | None = None,
    required_fields: str | None = None,
    description: str | None = None,
    unit: str | None = None,
    code: str | None = None,
    confirm: bool = False,
):
    """
    进化模式：创建计算器
    
    参数说明：
    - intent: 意图 (check_calculator / create_calculator)
    - field_name: 指标名称 (如 debt_to_ebitda)
    - formula: 计算公式
    - required_fields: 需要的输入字段 (逗号分隔)
    - description: 描述
    - unit: 单位
    - code: 完整的计算器代码
    - confirm: 是否确认应用
    """

    # -------------------------------------------------------------------------
    # 意图分支
    # -------------------------------------------------------------------------
    if intent == "check":
        return handle_check(field_name)

    if intent == "create":
        return handle_create(
            field_name=field_name,
            formula=formula,
            required_fields=required_fields,
            description=description,
            unit=unit,
            code=code,
            confirm=confirm,
        )

    # -------------------------------------------------------------------------
    # 默认：询问意图
    # -------------------------------------------------------------------------
    print("need: intent", file=sys.stdout, flush=True)
    print("  check   - 检查计算器是否存在", file=sys.stdout, flush=True)
    print("  create  - 创建新的计算器", file=sys.stdout, flush=True)


# =============================================================================
# 检查计算器
# =============================================================================

def handle_check(field_name: str | None):
    """检查计算器是否存在"""

    if not field_name:
        print("need: field_name", file=sys.stdout, flush=True)
        return

    # 检查是否存在
    calc = check_calculator(field_name)

    if calc:
        print(f"found: {field_name}", file=sys.stdout, flush=True)
        print(f"  description: {calc['description']}", file=sys.stdout, flush=True)
        print(f"  required_fields: {', '.join(calc['required_fields'])}", file=sys.stdout, flush=True)
    else:
        print(f"not_found: {field_name}", file=sys.stdout, flush=True)
        print("intent: create", file=sys.stdout, flush=True)
        print("skill: calculator_creation", file=sys.stdout, flush=True)
        print("need: --intent create --field-name {field_name}", file=sys.stdout, flush=True)


# =============================================================================
# 创建计算器
# =============================================================================

def handle_create(
    field_name: str | None,
    formula: str | None,
    required_fields: str | None,
    description: str | None,
    unit: str | None,
    code: str | None,
    confirm: bool,
):
    """创建新的计算器"""

    # -------------------------------------------------------------------------
    # 阶段 1: 收集参数
    # -------------------------------------------------------------------------
    missing = []
    if not field_name:
        missing.append("field_name")
    if not formula:
        missing.append("formula")
    if not required_fields:
        missing.append("required_fields")
    if not description:
        missing.append("description")
    if not unit:
        missing.append("unit")

    if missing:
        for item in missing:
            print(f"need: {item}", file=sys.stdout, flush=True)
        return

    # 输出收集到的参数
    print(f"field_name: {field_name}", file=sys.stdout, flush=True)
    print(f"formula: {formula}", file=sys.stdout, flush=True)
    print(f"required_fields: {required_fields}", file=sys.stdout, flush=True)
    print(f"description: {description}", file=sys.stdout, flush=True)
    print(f"unit: {unit}", file=sys.stdout, flush=True)

    # -------------------------------------------------------------------------
    # 阶段 2: 检查是否需要代码生成
    # -------------------------------------------------------------------------
    if not code:
        print("skill: calculator_creation", file=sys.stdout, flush=True)
        print("need: code_generation", file=sys.stdout, flush=True)
        print("need: --code <calculator_code>", file=sys.stdout, flush=True)
        return

    # -------------------------------------------------------------------------
    # 阶段 3: 确认应用
    # -------------------------------------------------------------------------
    if confirm:
        apply_calculator(field_name, code)
        print("done", file=sys.stdout, flush=True)
    else:
        print("need: --confirm", file=sys.stdout, flush=True)


# =============================================================================
# Skill 定义
# =============================================================================

def get_calculator_creation_skill() -> str:
    """
    Calculator 创建的 Skill
    """
    return '''# Calculator Creation Skill

## 场景
为 Value Investment 系统创建新的财务指标计算器。

## 输入参数
- field_name: 指标名称 (如 debt_to_ebitda, 必须 snake_case)
- formula: 计算公式 (如 "interest_bearing_debt / ebitda")
- required_fields: 需要的输入字段 (逗号分隔)
- description: 指标描述
- unit: 单位 (如 "ratio", "percent", "yuan")

## 代码规范

### 文件结构
```python
# calc_{field_name}.py

REQUIRED_FIELDS = ["field_a", "field_b"]

def calculate(data, config):
    """
    计算 {field_name}
    
    Args:
        data: dict[str, pd.Series]，字段数据，key=字段名，value=Series(index=年份)
        config: dict，用户配置
        
    Returns:
        pd.Series，计算结果
    """
    # 实现
    return data["field_a"] / data["field_b"]
```

### 字段映射示例
- interest_bearing_debt = 有息负债
- ebitda = 息税折旧摊销前利润
- net_profit = 净利润
- total_assets = 总资产
- total_equity = 净资产
- operating_cash_flow = 经营现金流

### 常见财务指标模式
```python
# 债务/EBITDA
return data["interest_bearing_debt"] / data["ebitda"]

# ROE
return data["net_profit"] / data["total_equity"]

# 毛利率
return (data["revenue"] - data["cost"]) / data["revenue"]
```

### 约束
- 必须定义 REQUIRED_FIELDS 列表
- 函数名必须是 calculate
- 参数必须是 data, config
- 返回必须是 pd.Series
- 禁止: eval, exec, open, import (除 pd), os, sys

## 示例
输入: debt_to_ebitda
输出:
```python
REQUIRED_FIELDS = ["interest_bearing_debt", "ebitda"]

def calculate(data, config):
    """
    债务/EBITDA比率，用于评估偿债能力
    
    公式: 有息负债 / EBITDA
    """
    debt = data["interest_bearing_debt"]
    ebitda = data["ebitda"]
    
    # 避免除零
    result = debt / ebitda.replace(0, float('nan'))
    return result
```
'''


# =============================================================================
# 应用计算器
# =============================================================================

def apply_calculator(field_name: str, code: str):
    """
    应用新创建的计算器
    
    写入到当前工作目录下的 calculators/ 目录，不存在则创建
    """
    from pathlib import Path

    # 验证代码格式
    if "REQUIRED_FIELDS" not in code:
        print("error: Missing REQUIRED_FIELDS", file=sys.stdout, flush=True)
        return

    if "def calculate" not in code:
        print("error: Missing calculate function", file=sys.stdout, flush=True)
        return

    # 使用当前工作目录
    calc_dir = Path.cwd() / "calculators"

    # 不存在则创建
    calc_dir.mkdir(parents=True, exist_ok=True)

    calc_file = calc_dir / f"calc_{field_name}.py"

    # 写入文件
    try:
        calc_file.write_text(code)
        print(f"written: {calc_file}", file=sys.stdout, flush=True)
    except Exception as e:
        print(f"error: Failed to write file: {e}", file=sys.stdout, flush=True)
        return

    # 注册到可用计算器
    AVAILABLE_CALCULATORS[field_name] = {
        "description": "用户创建",
        "required_fields": extract_required_fields(code),
    }

    print(f"registered: {field_name}", file=sys.stdout, flush=True)


def extract_required_fields(code: str) -> list:
    """从代码中提取 REQUIRED_FIELDS"""
    import re
    match = re.search(r'REQUIRED_FIELDS\s*=\s*\[(.*?)\]', code, re.DOTALL)
    if match:
        fields_str = match.group(1)
        # 提取引号内的字段名
        fields = re.findall(r'["\'](\w+)["\']', fields_str)
        return fields
    return []


# =============================================================================
# 主入口
# =============================================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(description='Calculator Creation + Evolution')

    # 意图
    parser.add_argument('--intent', help='意图 (check/create)')

    # 检查参数
    parser.add_argument('--field-name', help='指标名称')

    # 创建参数
    parser.add_argument('--formula', help='计算公式')
    parser.add_argument('--required-fields', help='需要的字段 (逗号分隔)')
    parser.add_argument('--description', help='描述')
    parser.add_argument('--unit', help='单位')
    parser.add_argument('--code', help='计算器代码')
    parser.add_argument('--confirm', action='store_true', help='确认应用')

    args = parser.parse_args()

    evolution_mode(
        intent=args.intent,
        field_name=args.field_name,
        formula=args.formula,
        required_fields=args.required_fields,
        description=args.description,
        unit=args.unit,
        code=args.code,
        confirm=args.confirm,
    )


if __name__ == "__main__":
    main()
