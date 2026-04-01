"""
毛利计算器（A股）
毛利 = 营收 - 营业成本
"""

REQUIRED_FIELDS = ["total_revenue", "operating_cost"]
SUPPORTED_MARKETS = ["A"]

FORMAT_TYPE = "absolute"

def calculate(data):
    """
    计算毛利

    公式: 毛利 = 营收 - 营业成本

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

    result = data["total_revenue"] - data["operating_cost"]
    return result
