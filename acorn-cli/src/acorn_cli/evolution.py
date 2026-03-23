"""
Evolution System - 数据筛选与转换场景
=====================================

通过 CLI 接口与 LLM Agent 交互，实现文件处理能力。

场景：读取 JSON 文件，按条件过滤和排序，输出结果文件。
"""

from __future__ import annotations

import json
import sys


# =============================================================================
# 当前能力：原样输出文件内容
# =============================================================================

def process_file(input_file: str, output_file: str | None = None) -> str:
    """当前实现：读取文件，原样输出"""
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            content = f.read()
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(content)
        return content
    except FileNotFoundError:
        return f"File not found: {input_file}"
    except Exception as e:
        return f"Error: {e}"


# =============================================================================
# Evolution 模式
# =============================================================================

def evolution_mode(
    intent: str | None = None,
    behavior: str | None = None,
    input_file: str | None = None,
    output_file: str | None = None,
    filter_rule: str | None = None,
    sort_key: str | None = None,
    confirm: bool = False,
    code: str | None = None,
):
    """
    进化模式：通过 print 与 LLM Agent 交互
    
    参数说明：
    - intent: 意图 (如 data_filter_transform)
    - behavior: 行为描述
    - input_file: 输入文件路径
    - output_file: 输出文件路径
    - filter_rule: 过滤规则
    - sort_key: 排序字段
    - code: LLM 生成的处理代码
    - confirm: 是否确认应用
    """
    
    # -------------------------------------------------------------------------
    # 阶段 1: 询问需求
    # -------------------------------------------------------------------------
    missing = []
    if not intent:
        missing.append("intent")
    if not behavior:
        missing.append("behavior")
    if not input_file:
        missing.append("input_file")
    if not output_file:
        missing.append("output_file")
    if not filter_rule:
        missing.append("filter_rule")
    if not sort_key:
        missing.append("sort_key")
    
    if missing:
        for item in missing:
            print(f"need: {item}", file=sys.stdout, flush=True)
        return
    
    # -------------------------------------------------------------------------
    # 阶段 2: 检查是否需要代码生成
    # -------------------------------------------------------------------------
    print(f"intent: {intent}", file=sys.stdout, flush=True)
    print(f"behavior: {behavior}", file=sys.stdout, flush=True)
    print(f"input: {input_file}", file=sys.stdout, flush=True)
    print(f"output: {output_file}", file=sys.stdout, flush=True)
    print(f"filter: {filter_rule}", file=sys.stdout, flush=True)
    print(f"sort: {sort_key}", file=sys.stdout, flush=True)
    
    if not code:
        print("skill: data_filter", file=sys.stdout, flush=True)
        print("need: code_generation", file=sys.stdout, flush=True)
        return
    
    # -------------------------------------------------------------------------
    # 阶段 3: 确认应用
    # -------------------------------------------------------------------------
    if confirm:
        apply_code(code, input_file, output_file, filter_rule, sort_key)
        print("done", file=sys.stdout, flush=True)
    else:
        print("need: --confirm", file=sys.stdout, flush=True)


# =============================================================================
# Skill 定义
# =============================================================================

def get_data_filter_skill() -> str:
    """
    数据筛选与转换的 Skill
    """
    return '''# Data Filter Transform Skill

## 场景
读取 JSON 文件，按条件过滤数据，按指定字段排序，输出到目标文件。

## 输入
- input_file: JSON 文件路径（数组格式）
- filter_rule: 过滤规则描述
- sort_key: 排序字段

## 输出
- output_file: 结果 JSON 文件

## 代码规范

### 函数签名
```python
def process(input_file: str, output_file: str, filter_rule: str, sort_key: str) -> None:
    """
    处理数据文件
    
    Args:
        input_file: 输入 JSON 文件路径
        output_file: 输出 JSON 文件路径
        filter_rule: 过滤规则描述
        sort_key: 排序字段名
    """
    # 1. 读取输入文件
    # 2. 根据 filter_rule 过滤数据
    # 3. 按 sort_key 排序
    # 4. 写入输出文件
```

### 实现提示

1. 读取 JSON 文件
```python
with open(input_file, 'r', encoding='utf-8') as f:
    data = json.load(f)
```

2. 过滤数据（filter_rule 示例）
- "年龄 18-30 岁" → item.get('age', 0) >= 18 and item.get('age', 0) <= 30
- "城市是北京" → item.get('city') == '北京'
- "名字以张开头" → item.get('name', '').startswith('张')

3. 排序
```python
data.sort(key=lambda x: x.get(sort_key, ''))
```

4. 写入 JSON
```python
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
```

## 约束
- 只允许 json, file 操作
- 禁止: eval, exec, open (除指定文件), import (除 json)
'''


# =============================================================================
# 代码应用
# =============================================================================

def apply_code(
    code: str,
    input_file: str,
    output_file: str,
    filter_rule: str,
    sort_key: str
):
    """
    应用生成的代码
    
    解析函数定义，执行并生成结果
    """
    # 构建全局命名空间
    namespace = {
        '__builtins__': {'json': json, 'open': open},
        'json': json,
        'open': open,
    }
    
    # 执行代码
    exec(code, namespace)
    
    # 调用 process 函数
    if 'process' in namespace:
        # 转换相对路径为绝对路径
        import os
        abs_input = os.path.abspath(input_file)
        abs_output = os.path.abspath(output_file)
        
        namespace['process'](abs_input, abs_output, filter_rule, sort_key)
        print(f"output: {abs_output}", file=sys.stdout, flush=True)


# =============================================================================
# 主入口
# =============================================================================

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='文件处理 + Evolution')
    parser.add_argument('input', nargs='?', help='输入文件')
    parser.add_argument('--evolve', action='store_true', help='进入进化模式')
    parser.add_argument('--intent', help='意图')
    parser.add_argument('--behavior', help='行为描述')
    parser.add_argument('--input-file', help='输入文件路径')
    parser.add_argument('--output-file', help='输出文件路径')
    parser.add_argument('--filter-rule', help='过滤规则')
    parser.add_argument('--sort-key', help='排序字段')
    parser.add_argument('--confirm', action='store_true', help='确认应用')
    parser.add_argument('--code', help='LLM 生成的代码')
    
    args = parser.parse_args()
    
    if args.evolve:
        evolution_mode(
            intent=args.intent,
            behavior=args.behavior,
            input_file=args.input_file,
            output_file=args.output_file,
            filter_rule=args.filter_rule,
            sort_key=args.sort_key,
            confirm=args.confirm,
            code=args.code,
        )
    else:
        # 普通模式
        if args.input:
            result = process_file(args.input)
            print(result)


if __name__ == "__main__":
    main()
