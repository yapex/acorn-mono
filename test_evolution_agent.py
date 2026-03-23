#!/usr/bin/env python3
"""
模拟 LLM Agent 与 Evolution System 交互

这个脚本模拟 LLM Agent 的行为：
1. 读取程序的输出 (stdout)
2. 理解需求
3. 提供输入 (通过命令行参数)
"""

import subprocess
import re
import sys

def run_evolution(args: list[str]) -> tuple[str, int]:
    """运行 evolution 命令，返回 (stdout, returncode)"""
    result = subprocess.run(
        ["python", "-m", "acorn_cli.evolution"] + args,
        capture_output=True,
        text=True,
        cwd="acorn-cli/src",
    )
    return result.stdout, result.returncode


def parse_needs(output: str) -> dict[str, str]:
    """解析程序的 'need: xxx' 输出"""
    needs = {}
    for line in output.split('\n'):
        if line.startswith('need:'):
            # 格式: need: key=value 或 need: key=?
            match = re.match(r'need:\s*(\w+)=(.+)', line)
            if match:
                key, value = match.groups()
                needs[key] = value
    return needs


def simulate_llm_agent(user_goal: str):
    """
    模拟 LLM Agent 的决策过程
    
    实际场景中，这里会调用 LLM 来理解需求
    """
    print(f"🎯 用户目标: {user_goal}")
    print()
    
    # 第一次运行：获取程序的需求
    print("📤 第一步: 读取程序需求")
    output, _ = run_evolution(["--evolve"])
    print(output)
    
    needs = parse_needs(output)
    print(f"📋 解析到的需求: {needs}")
    print()
    
    # LLM 理解需求后，提供信息
    # 这里简化处理，实际应该调用 LLM
    print("🤖 LLM Agent 理解需求...")
    
    # 构造第二次运行的参数
    args = ["--evolve"]
    
    if needs.get('intent') == '?':
        # 根据用户目标推断 intent
        args.extend(["--intent", "translation"])
    
    if needs.get('expected_behavior') == '?':
        args.extend(["--behavior", "中文翻译成英文，英文翻译成中文"])
    
    # 第二次运行
    print(f"📤 第二步: 提供需求，生成代码")
    output, _ = run_evolution(args)
    print(output)
    
    # 检查是否需要确认
    if "need: --confirm" in output:
        print("📤 第三步: 确认应用")
        args.append("--confirm")
        output, _ = run_evolution(args)
        print(output)
    
    print("✅ 进化完成!")


if __name__ == "__main__":
    # 模拟用户说 "帮我把中文翻译成英文"
    user_goal = "帮我把中文翻译成英文，英文翻译成中文"
    simulate_llm_agent(user_goal)
