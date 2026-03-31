"""
产权比率计算器（港股）
产权比率 = 总负债 / 总权益
"""

REQUIRED_FIELDS = ["total_liabilities", "total_equity"]
MARKET_CODES = ["HK"]

def calculate(data):
    """
    计算产权比率

    公式: 产权比率 = 总负债 / 总权益

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

    result = data["total_liabilities"] / data["total_equity"].replace(0, float('nan'))
    return result
