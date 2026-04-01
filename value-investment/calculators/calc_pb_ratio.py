"""
市净率计算器（美股）
市净率 = 总市值 / 股东权益合计
"""

REQUIRED_FIELDS = ["market_cap", "total_equity"]
SUPPORTED_MARKETS = ["US"]

FORMAT_TYPE = "ratio"

def calculate(data):
    """
    计算市净率

    公式: 市净率 = 总市值 / 股东权益合计

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

    result = data["market_cap"] / data["total_equity"].replace(0, float('nan'))
    return result
