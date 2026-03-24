#!/usr/bin/env python3
"""
模拟 LLM Agent 与 Evolution System 交互
场景：Calculator 创建
"""

import subprocess
import json

def run_evolution(args: list[str]) -> tuple[str, int]:
    result = subprocess.run(
        ["python", "-m", "acorn_cli.evolution"] + args,
        capture_output=True,
        text=True,
        cwd="acorn-cli/src",
    )
    return result.stdout, result.returncode


def simulate_llm_agent(user_question: str):
    print(f"🎯 用户: {user_question}")
    print()
    
    # 阶段1: 检查计算器是否存在
    print("📤 阶段1: 检查计算器是否存在")
    
    # 从用户问题中提取字段名
    # 简化：假设用户问的是 debt_to_ebitda
    field_name = "debt_to_ebitda"
    
    output, _ = run_evolution([
        "--intent", "check",
        "--field-name", field_name,
    ])
    print(output)
    
    # 检查结果
    if "not_found:" in output:
        print(f"📤 字段 {field_name} 不存在，需要创建")
        print()
        
        # 阶段2: 创建计算器 - 提供基本信息
        print("📤 阶段2: 创建计算器 - 提供基本信息")
        output, _ = run_evolution([
            "--intent", "create",
            "--field-name", field_name,
            "--formula", "interest_bearing_debt / ebitda",
            "--required-fields", "interest_bearing_debt,ebitda",
            "--description", "债务/EBITDA比率，用于评估偿债能力",
            "--unit", "ratio",
        ])
        print(output)
        
        # 检查是否需要代码
        if "need: code_generation" in output:
            print("📤 阶段2.5: LLM Agent 根据 Skill 生成代码")
            
            # 根据 Skill 生成的代码
            generated_code = '''REQUIRED_FIELDS = ["interest_bearing_debt", "ebitda"]

def calculate(data, config):
    """
    债务/EBITDA比率，用于评估偿债能力
    
    公式: 有息负债 / EBITDA
    
    Args:
        data: dict[str, pd.Series]，字段数据
        config: dict，用户配置
        
    Returns:
        pd.Series，计算结果
    """
    debt = data["interest_bearing_debt"]
    ebitda = data["ebitda"]
    
    # 避免除零
    result = debt / ebitda.replace(0, float('nan'))
    return result'''
            
            print(f"生成代码长度: {len(generated_code)} 字符")
            print()
            
            # 继续执行，提供代码
            output, _ = run_evolution([
                "--intent", "create",
                "--field-name", field_name,
                "--formula", "interest_bearing_debt / ebitda",
                "--required-fields", "interest_bearing_debt,ebitda",
                "--description", "债务/EBITDA比率，用于评估偿债能力",
                "--unit", "ratio",
                "--code", generated_code,
            ])
            print(output)
            
            # 阶段3: 确认
            if "need: --confirm" in output:
                print("📤 阶段3: 确认应用")
                output, _ = run_evolution([
                    "--intent", "create",
                    "--field-name", field_name,
                    "--formula", "interest_bearing_debt / ebitda",
                    "--required-fields", "interest_bearing_debt,ebitda",
                    "--description", "债务/EBITDA比率，用于评估偿债能力",
                    "--unit", "ratio",
                    "--code", generated_code,
                    "--confirm",
                ])
                print(output)
                
                # 验证：再次检查
                print("📤 验证: 再次检查计算器")
                output, _ = run_evolution([
                    "--intent", "check",
                    "--field-name", field_name,
                ])
                print(output)
    
    print("✅ 完成")


if __name__ == "__main__":
    simulate_llm_agent("能帮我计算 debt_to_ebitda 吗？")
