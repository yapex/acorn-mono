"""
波动率计算器
波动率 = 标准差 / 均值
衡量数据的离散程度，用于评估指标的稳定性
"""

REQUIRED_FIELDS = ["roe"]
SUPPORTED_MARKETS = ["A", "HK", "US"]

def calculate(data):
    """
    计算波动率（变异系数）

    公式: 波动率 = 标准差 / 均值
    值越低说明数据越稳定，用于评估 ROE 等指标的长期稳定性

    Args:
        data: dict[str, pd.Series] - 字段数据，Series index 为年份

    Returns:
        float - 波动率值（如 0.15 表示 15%）
    """
    import pandas as pd
    import numpy as np

    series = data["roe"].dropna()

    if len(series) < 2:
        return float('nan')

    mean_val = series.mean()
    if mean_val == 0 or pd.isna(mean_val):
        return float('nan')

    volatility = series.std() / abs(mean_val)
    return float(volatility)
