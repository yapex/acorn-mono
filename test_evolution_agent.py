#!/usr/bin/env python3
"""
模拟 LLM Agent 与 Evolution System 交互
"""

import subprocess
import re

def run_evolution(args: list[str]) -> tuple[str, int]:
    result = subprocess.run(
        ["python", "-m", "acorn_cli.evolution"] + args,
        capture_output=True,
        text=True,
        cwd="acorn-cli/src",
    )
    return result.stdout, result.returncode


def parse_needs(output: str) -> list[str]:
    """解析 'need: xxx' 输出"""
    return [line.replace("need:", "").strip() 
            for line in output.split('\n') 
            if line.startswith('need:')]


def simulate_llm_agent(user_goal: str):
    print(f"🎯 用户: {user_goal}")
    print()
    
    # 阶段1: 读取需求
    print("📤 读取程序需求")
    output, _ = run_evolution(["--evolve"])
    needs = parse_needs(output)
    print(output)
    
    # 阶段2: 提供需求
    print("📤 提供需求")
    args = ["--evolve"]
    for need in needs:
        if need == "intent":
            args.extend(["--intent", "translation"])
        elif need == "behavior":
            args.extend(["--behavior", "中文翻译成英文，英文翻译成中文"])
    
    output, _ = run_evolution(args)
    print(output)
    
    # 阶段3: 确认
    if "need: --confirm" in output:
        print("📤 确认应用")
        output, _ = run_evolution(args + ["--confirm"])
        print(output)
    
    print("✅ 完成")


if __name__ == "__main__":
    simulate_llm_agent("帮我把中文翻译成英文")
