"""
营业利润率计算器（港股）
营业利润率 = 营业利润 / 营收
"""

REQUIRED_FIELDS = ["operating_profit", "total_revenue"]
MARKET_CODES = ["HK", "US"]

def calculate(data):
    """
    计算营业利润率

    公式: 营业利润率 = 营业利润 / 营收

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

    result = data["operating_profit"] / data["total_revenue"].replace(0, float('nan'))
    return result
