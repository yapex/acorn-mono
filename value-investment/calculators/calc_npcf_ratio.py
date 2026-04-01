"""
净现比计算器
净现比 = 经营现金流 / 净利润
反映盈利质量，经营现金流与净利润的比率
"""

REQUIRED_FIELDS = ["operating_cash_flow", "net_profit"]

FORMAT_TYPE = "ratio"

def calculate(data):
    """
    计算净现比
    
    净现比 = 经营现金流 / 净利润
    用于评估盈利质量，比值越高说明净利润中现金含量越高
    
    Args:
        data: dict[str, pd.Series] - 字段数据
        
    Returns:
        pd.Series - 计算结果
    """
    ocf = data["operating_cash_flow"]
    np_ = data["net_profit"]

    # 避免除零
    result = ocf / np_.replace(0, float('nan'))
    return result
