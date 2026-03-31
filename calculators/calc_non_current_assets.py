"""
非流动资产计算器（A股）
非流动资产 = 总资产 - 流动资产
"""

REQUIRED_FIELDS = ["total_assets", "current_assets"]
SUPPORTED_MARKETS = ["A"]

def calculate(data):
    """
    计算非流动资产

    公式: 非流动资产 = 总资产 - 流动资产

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

    result = data["total_assets"] - data["current_assets"]
    return result
