"""
非流动负债计算器（A股）
非流动负债 = 总负债 - 流动负债
"""

REQUIRED_FIELDS = ["total_liabilities", "current_liabilities"]
SUPPORTED_MARKETS = ["A", "HK", "US"]

FORMAT_TYPE = "absolute"

def calculate(data):
    """
    计算非流动负债

    公式: 非流动负债 = 总负债 - 流动负债

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

    result = data["total_liabilities"] - data["current_liabilities"]
    return result
