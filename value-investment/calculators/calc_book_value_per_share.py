"""
每股净资产计算器（美股）
每股净资产 = 股东权益合计 / 总股本
"""

REQUIRED_FIELDS = ["total_equity", "total_shares"]
SUPPORTED_MARKETS = ["US"]

FORMAT_TYPE = "absolute"

def calculate(data):
    """
    计算每股净资产

    公式: 每股净资产 = 股东权益合计 / 总股本

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

    result = data["total_equity"] / data["total_shares"].replace(0, float('nan'))
    return result
