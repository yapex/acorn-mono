"""
速动比率计算器（港股）
速动比率 = (流动资产 - 存货) / 流动负债
"""

REQUIRED_FIELDS = ["current_assets", "inventory", "current_liabilities"]
SUPPORTED_MARKETS = ["HK"]

FORMAT_TYPE = "ratio"

def calculate(data):
    """
    计算速动比率

    公式: 速动比率 = (流动资产 - 存货) / 流动负债

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

    result = (data["current_assets"] - data["inventory"]) / data["current_liabilities"].replace(0, float('nan'))
    return result
