"""
复合年增长率计算器
CAGR = (终值/初值)^(1/n) - 1
衡量一段时间内的平均年增长率
"""

REQUIRED_FIELDS = ["total_revenue"]
SUPPORTED_MARKETS = ["A", "HK", "US"]

def calculate(data):
    """
    计算复合年增长率 CAGR

    公式: CAGR = (终值/初值)^(1/n) - 1
    n 为首末之间的年数，返回单值（标量）

    Args:
        data: dict[str, pd.Series] - 字段数据，Series index 为年份

    Returns:
        float - CAGR 值（如 0.15 表示 15%）
    """
    import pandas as pd
    import numpy as np

    series = data["total_revenue"].dropna()

    if len(series) < 2:
        return float('nan')

    # 取第一个和最后一个有效值
    start_value = series.iloc[0]
    end_value = series.iloc[-1]

    if start_value <= 0 or end_value <= 0 or pd.isna(start_value) or pd.isna(end_value):
        return float('nan')

    n = len(series) - 1  # 年数 = 数据点数 - 1
    cagr = (end_value / start_value) ** (1 / n) - 1
    return float(cagr)
