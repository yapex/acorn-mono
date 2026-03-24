#!/usr/bin/env python3
"""
测试 LLM Agent 进化流程

模拟：
1. Calculator 不存在 → 发布事件 → EvoManager print prompt
2. LLM Agent 收到 prompt，生成代码
3. 注册 Calculator
4. 再次查询，Calculator 存在
"""

import pandas as pd
from unittest.mock import MagicMock


def test_llm_agent_evolution():
    """完整的 LLM Agent 进化流程测试"""
    
    print("=" * 60)
    print("测试 LLM Agent 进化流程")
    print("=" * 60)
    
    # -------------------------------------------------------------------------
    # Phase 1: 初始化系统
    # -------------------------------------------------------------------------
    print("\n>>> Phase 1: 初始化系统\n")
    
    from acorn_core.plugins.evo_manager import EvoManager
    from vi_core.plugin import ViCorePlugin
    
    evo = EvoManager()
    evo.on_load()
    
    plugin = ViCorePlugin()
    
    # Mock plugin manager
    mock_pm = MagicMock()
    mock_pm.hook.vi_list_calculators.return_value = [[]]  # 空的 calculator 列表
    ViCorePlugin._pm = mock_pm
    
    # -------------------------------------------------------------------------
    # Phase 2: 请求不存在的 Calculator
    # -------------------------------------------------------------------------
    print(">>> Phase 2: 请求不存在的 Calculator\n")
    
    df = pd.DataFrame({
        'interest_bearing_debt': [100, 120, 140],
        'ebitda': [50, 60, 70],
    }, index=[2020, 2021, 2022])
    
    # 这会触发 EvoManager print prompt
    result = plugin._run_calculators(df, {'debt_to_ebitda'}, {})
    print(f"\n计算结果（应该为空）: {result}")
    
    # -------------------------------------------------------------------------
    # Phase 3: LLM Agent 生成代码
    # -------------------------------------------------------------------------
    print("\n>>> Phase 3: LLM Agent 根据 Prompt 生成代码\n")
    
    # LLM Agent 生成的代码
    generated_code = '''REQUIRED_FIELDS = ["interest_bearing_debt", "ebitda"]

def calculate(data, config):
    """
    债务/EBITDA 比率，用于评估偿债能力
    
    Args:
        data: dict[str, pd.Series] - 字段数据
        config: dict - 用户配置
        
    Returns:
        pd.Series - 计算结果
    """
    debt = data["interest_bearing_debt"]
    ebitda = data["ebitda"]
    
    # 避免除零
    result = debt / ebitda.replace(0, float("nan"))
    return result
'''
    
    print("生成的代码:")
    print("-" * 40)
    print(generated_code)
    print("-" * 40)
    
    # -------------------------------------------------------------------------
    # Phase 4: 注册 Calculator
    # -------------------------------------------------------------------------
    print("\n>>> Phase 4: 注册 Calculator\n")
    
    # 模拟注册成功
    def mock_register(name, code, required_fields, description, namespace):
        print(f"注册 Calculator: {name}")
        print(f"  required_fields: {required_fields}")
        print(f"  description: {description}")
        
        # 将 calculator 添加到 mock registry
        mock_pm.hook.vi_list_calculators.return_value = [[
            {"name": name, "required_fields": required_fields, "description": description}
        ]]
        
        # 动态执行代码验证
        local_vars = {}
        exec(code, local_vars)
        
        # 保存 calculate 函数
        mock_pm._calculators = {name: local_vars}
        
        return {"success": True, "data": {"name": name}}
    
    mock_pm.hook.vi_register_calculator.side_effect = mock_register
    
    result = plugin._register_calculator({
        'name': 'debt_to_ebitda',
        'code': generated_code,
        'required_fields': ['interest_bearing_debt', 'ebitda'],
        'description': '债务/EBITDA比率',
    })
    
    print(f"注册结果: {result}")
    
    # -------------------------------------------------------------------------
    # Phase 5: 再次请求，Calculator 已存在
    # -------------------------------------------------------------------------
    print("\n>>> Phase 5: 再次请求，Calculator 已存在\n")
    
    # 模拟 vi_run_calculator
    def mock_run_calculator(name, data, config):
        if name in getattr(mock_pm, '_calculators', {}):
            calc_func = mock_pm._calculators[name].get('calculate')
            if calc_func:
                return calc_func(data, config)
        return None
    
    mock_pm.hook.vi_run_calculator.side_effect = mock_run_calculator
    
    result = plugin._run_calculators(df, {'debt_to_ebitda'}, {})
    print(f"计算结果: {result}")
    
    # -------------------------------------------------------------------------
    # 总结
    # -------------------------------------------------------------------------
    print("\n" + "=" * 60)
    print("✅ 进化流程测试完成")
    print("=" * 60)
    
    print(f"\nEvoManager 记录的扩展请求: {len(evo.extension_requests)} 条")
    for req in evo.extension_requests:
        print(f"  - {req['calculator_name']}")


if __name__ == "__main__":
    test_llm_agent_evolution()
