"""
流动负债/总负债计算器（美股）
流动负债占总负债比例 = 流动负债 / 总负债
"""

REQUIRED_FIELDS = ["current_liabilities", "total_liabilities"]
MARKET_CODES = ["US"]

def calculate(data):
    """
    计算流动负债占总负债比例

    公式: 流动负债/总负债 = 流动负债 / 总负债

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

    result = data["current_liabilities"] / data["total_liabilities"].replace(0, float('nan'))
    return result
