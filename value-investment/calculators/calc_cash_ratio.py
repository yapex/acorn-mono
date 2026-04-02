"""
现金比率计算器
现金比率 = 现金及现金等价物 / 流动负债
"""

REQUIRED_FIELDS = ["cash_and_equivalents", "current_liabilities"]
SUPPORTED_MARKETS = ["A", "HK", "US"]

FORMAT_TYPE = "ratio"

def calculate(data):
    """
    计算现金比率

    公式: 现金比率 = 现金及现金等价物 / 流动负债

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

    result = data["cash_and_equivalents"] / data["current_liabilities"].replace(0, float('nan'))
    return result
