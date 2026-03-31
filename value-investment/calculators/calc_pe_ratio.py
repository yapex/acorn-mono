"""
市盈率计算器（美股）
市盈率 = 总市值 / 归属母公司净利润
"""

REQUIRED_FIELDS = ["market_cap", "parent_net_profit"]
MARKET_CODES = ["US"]

def calculate(data):
    """
    计算市盈率

    公式: 市盈率 = 总市值 / 归属母公司净利润

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

    result = data["market_cap"] / data["parent_net_profit"].replace(0, float('nan'))
    return result
