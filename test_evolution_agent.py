#!/usr/bin/env python3
"""
模拟 LLM Agent 与 Evolution System 交互
场景：数据筛选与转换
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


def simulate_llm_agent(user_goal: str):
    print(f"🎯 用户: {user_goal}")
    print()
    
    import os
    # 获取项目根目录
    project_root = os.path.dirname(os.path.abspath(__file__))
    input_file = os.path.join(project_root, "test_data", "people.json")
    output_file = os.path.join(project_root, "test_data", "result.json")
    
    # 阶段1: 提供基本信息
    print("📤 阶段1: 提供 intent, behavior")
    output, _ = run_evolution([
        "--evolve",
        "--intent", "data_filter_transform",
        "--behavior", "过滤并排序",
    ])
    print(output)
    
    # 检测是否需要更多参数
    needs_more = "need: input_file" in output or "need: filter_rule" in output
    
    if needs_more:
        print("📤 阶段1.5: 提供文件路径和过滤规则")
        output, _ = run_evolution([
            "--evolve",
            "--intent", "data_filter_transform",
            "--behavior", "过滤并排序",
            "--input-file", input_file,
            "--output-file", output_file,
            "--filter-rule", "年龄 18-30 岁",
            "--sort-key", "name",
        ])
        print(output)
    
    # 检测是否需要代码生成
    if "need: code_generation" in output:
        print("📤 阶段2: LLM Agent 生成代码")
        
        # 模拟 LLM 根据 skill 生成的代码
        generated_code = '''def process(input_file: str, output_file: str, filter_rule: str, sort_key: str) -> None:
    """
    处理数据文件
    
    Args:
        input_file: 输入 JSON 文件路径
        output_file: 输出 JSON 文件路径
        filter_rule: 过滤规则描述
        sort_key: 排序字段名
    """
    # 读取输入文件
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 过滤: 年龄 18-30 岁
    def matches_filter(item):
        age = item.get('age', 0)
        return age >= 18 and age <= 30
    
    result = [item for item in data if matches_filter(item)]
    
    # 排序: 按 name
    result.sort(key=lambda x: x.get(sort_key, ''))
    
    # 写入输出文件
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
'''
        
        print(f"生成代码长度: {len(generated_code)} 字符")
        print()
        
        # 继续执行，提供 code
        output, _ = run_evolution([
            "--evolve",
            "--intent", "data_filter_transform",
            "--behavior", "过滤并排序",
            "--input-file", input_file,
            "--output-file", output_file,
            "--filter-rule", "年龄 18-30 岁",
            "--sort-key", "name",
            "--code", generated_code,
        ])
        print(output)
    
    # 阶段3: 确认
    if "need: --confirm" in output:
        print("📤 阶段3: 确认应用")
        output, _ = run_evolution([
            "--evolve",
            "--intent", "data_filter_transform",
            "--behavior", "过滤并排序",
            "--input-file", input_file,
            "--output-file", output_file,
            "--filter-rule", "年龄 18-30 岁",
            "--sort-key", "name",
            "--code", generated_code,
            "--confirm",
        ])
        print(output)
        
        # 检查输出文件
        try:
            with open("test_data/result.json", 'r', encoding='utf-8') as f:
                result = json.load(f)
            print("📄 输出结果:")
            print(json.dumps(result, ensure_ascii=False, indent=2))
        except FileNotFoundError:
            print("⚠️ 结果文件未生成（代码执行部分未完整实现）")
    
    print("✅ 完成")


if __name__ == "__main__":
    simulate_llm_agent("读取 people.json，过滤出 18-30 岁的人，按姓名排序")
