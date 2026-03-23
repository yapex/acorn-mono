#!/usr/bin/env python3
"""
模拟 LLM Agent 与 Evolution System 交互
"""

import subprocess

def run_evolution(args: list[str]) -> tuple[str, int]:
    result = subprocess.run(
        ["python", "-m", "acorn_cli.evolution"] + args,
        capture_output=True,
        text=True,
        cwd="acorn-cli/src",
    )
    return result.stdout, result.returncode


def simulate_llm_agent(user_goal: str):
    print(f"🎯 用户: {user_goal}")
    print()
    
    # 阶段1: 提供 intent, behavior
    print("📤 阶段1: 提供 intent, behavior")
    output, _ = run_evolution([
        "--evolve",
        "--intent", "translation",
        "--behavior", "中文翻译成英文"
    ])
    print(output)
    
    # 检测是否需要代码生成
    if "need: code_generation" in output:
        # 阶段2: LLM Agent 生成代码（这里模拟）
        print("📤 阶段2: LLM Agent 生成代码")
        generated_code = '''def translate(text: str) -> str:
    if "你好" in text:
        return "hello"
    return text'''
        
        # 提供 code 参数再次运行
        output, _ = run_evolution([
            "--evolve",
            "--intent", "translation",
            "--behavior", "中文翻译成英文",
            "--code", generated_code
        ])
        print(output)
    
    # 阶段3: 确认
    if "need: --confirm" in output:
        print("📤 阶段3: 确认应用")
        output, _ = run_evolution([
            "--evolve",
            "--intent", "translation",
            "--behavior", "中文翻译成英文",
            "--code", generated_code,
            "--confirm"
        ])
        print(output)
    
    print("✅ 完成")


if __name__ == "__main__":
    simulate_llm_agent("帮我把中文翻译成英文")
