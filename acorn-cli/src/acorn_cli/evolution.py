"""
Evolution System - 最小原型
===========================

通过 CLI 接口与 LLM Agent 交互，实现自我进化。

对话协议：
- 程序通过 print 输出需求 ("need: xxx")
- 程序通过 input() 接收信息
- LLM Agent 读取 stdout，理解后提供输入
"""

from __future__ import annotations

import sys


# =============================================================================
# 当前 Echo 插件能力
# =============================================================================

def echo_current(text: str) -> str:
    """当前 Echo 实现：原样返回输入"""
    return text


# =============================================================================
# Evolution 模式
# =============================================================================

def evolution_mode(intent: str | None = None, behavior: str | None = None, confirm: bool = False, code: str | None = None):
    """
    进化模式：通过 print/input 与 LLM Agent 交互
    
    阶段：
    1. 询问需求 (need: xxx)
    2. 接收需求 (从 input)
    3. 生成代码 (loading_skill, generating)
    4. 确认应用 (confirm)
    """
    
    # -------------------------------------------------------------------------
    # 阶段 1: 询问需求
    # -------------------------------------------------------------------------
    if not intent:
        print("need: intent", file=sys.stdout, flush=True)
        print("need: behavior", file=sys.stdout, flush=True)
        return
    
    # -------------------------------------------------------------------------
    # 阶段 2: 接收需求
    # -------------------------------------------------------------------------
    print(f"skill: translation", file=sys.stdout, flush=True)
    
    # 如果没有 code，说明是第一次运行，需要 LLM 生成代码
    if not code:
        print("need: code_generation", file=sys.stdout, flush=True)
        print("need: --code <generated_code>", file=sys.stdout, flush=True)
        return
    
    # -------------------------------------------------------------------------
    # 阶段 3: 确认应用
    # -------------------------------------------------------------------------
    if confirm:
        apply_code(code)
        print("done", file=sys.stdout, flush=True)
    else:
        print("need: --confirm", file=sys.stdout, flush=True)


# =============================================================================
# Skill 定义
# =============================================================================

def get_translation_skill() -> str:
    """
    返回翻译场景的 Skill 内容
    
    这段内容会被传递给 LLM，让它知道如何生成代码
    """
    return '''# Translation Skill

## 场景
创建一个翻译函数：中文翻译成英文，英文翻译成中文

## 输入输出
- 输入: 字符串文本
- 输出: 翻译后的字符串

## 代码规范
```python
def translate(text: str) -> str:
    """
    翻译函数
    
    Args:
        text: 输入文本
        
    Returns:
        翻译后的文本
    """
    # 实现翻译逻辑
    return result
```

## 实现提示
1. 检测文本是否包含中文字符
2. 如果是中文，使用翻译逻辑转英文
3. 如果是英文，使用翻译逻辑转中文
4. 返回翻译结果

## 约束
- 只允许字符串操作
- 禁止: eval, exec, open, import
'''


# =============================================================================
# 代码生成
# =============================================================================

def generate_translation_code(intent: str, behavior: str) -> str:
    """
    根据 intent 和 behavior 生成翻译代码
    
    这里是一个简化实现，实际应该调用 LLM
    """
    # 简化：直接生成一个模板代码
    code = '''def translate(text: str) -> str:
    """
    翻译函数: 中文→英文, 英文→中文
    
    Args:
        text: 输入文本
    Returns:
        翻译后的文本
    """
    import re
    
    # 检测是否包含中文字符
    has_chinese = bool(re.search(r'[\\u4e00-\\u9fff]', text))
    
    if has_chinese:
        # 中文 → 英文 (简化实现，需要真实翻译 API)
        chinese_to_english = {
            "你好": "hello",
            "谢谢": "thank you",
            "再见": "goodbye",
            "早上好": "good morning",
            "晚上好": "good evening",
        }
        return chinese_to_english.get(text, f"[EN:{text}]")
    else:
        # 英文 → 中文 (简化实现，需要真实翻译 API)
        english_to_chinese = {
            "hello": "你好",
            "thank you": "谢谢",
            "goodbye": "再见",
            "good morning": "早上好",
            "good evening": "晚上好",
        }
        return english_to_chinese.get(text.lower(), f"[中:{text}]")'''
    
    return code


def apply_code(code: str):
    """应用生成的代码"""
    # 简化实现：将代码写入临时模块
    # 实际应该写入插件目录
    pass


# =============================================================================
# 主入口
# =============================================================================

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Echo with Evolution')
    parser.add_argument('input', nargs='?', help='输入文本')
    parser.add_argument('--evolve', action='store_true', help='进入进化模式')
    parser.add_argument('--intent', help='意图')
    parser.add_argument('--behavior', help='期望行为')
    parser.add_argument('--confirm', action='store_true', help='确认应用')
    parser.add_argument('--code', help='LLM 生成的代码')
    
    args = parser.parse_args()
    
    if args.evolve:
        evolution_mode(
            intent=args.intent,
            behavior=args.behavior,
            confirm=args.confirm,
            code=args.code
        )
    else:
        # 普通模式
        result = echo_current(args.input or "")
        print(result)


if __name__ == "__main__":
    main()
