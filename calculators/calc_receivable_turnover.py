"""
应收账款周转率计算器（美股）
应收账款周转率 = 营收 / 应收账款
"""

REQUIRED_FIELDS = ["total_revenue", "accounts_receivable"]
SUPPORTED_MARKETS = ["HK", "US"]

def calculate(data):
    """
    计算应收账款周转率

    公式: 应收账款周转率 = 营收 / 应收账款

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

    result = data["total_revenue"] / data["accounts_receivable"].replace(0, float('nan'))
    return result
