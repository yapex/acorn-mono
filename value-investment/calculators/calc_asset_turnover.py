"""
资产周转率计算器（美股）
资产周转率 = 营收 / 总资产
"""

REQUIRED_FIELDS = ["total_revenue", "total_assets"]
MARKET_CODES = ["HK", "US"]

def calculate(data):
    """
    计算资产周转率

    公式: 资产周转率 = 营收 / 总资产

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

    result = data["total_revenue"] / data["total_assets"].replace(0, float('nan'))
    return result
