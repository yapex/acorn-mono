"""
净负债率计算器
净负债率 = (有息负债 - 货币资金) / 净资产
反映企业扣除现金后的真实杠杆水平
"""

REQUIRED_FIELDS = ["interest_bearing_debt", "cash_and_equivalents", "total_equity"]
SUPPORTED_MARKETS = ["A", "HK", "US"]

def calculate(data):
    """
    计算净负债率

    公式: 净负债率 = (有息负债 - 货币资金) / 净资产
    负值表示净现金状态，正值表示净负债状态

    Args:
        data: dict[str, pd.Series] - 字段数据

    Returns:
        pd.Series - 计算结果
    """
    import pandas as pd

    for field in REQUIRED_FIELDS:
        if field not in data:
            return pd.Series(dtype=float)
        if data[field].isna().all():
            return pd.Series(dtype=float)

    net_debt = data["interest_bearing_debt"] - data["cash_and_equivalents"]
    result = net_debt / data["total_equity"].replace(0, float('nan'))
    return result
