"""
利息保障倍数计算器
利息保障倍数 = 经营利润 / 利息支出
反映企业用经营利润支付利息的能力
"""

REQUIRED_FIELDS = ["operating_profit", "interest_expense"]
SUPPORTED_MARKETS = ["A", "HK", "US"]

def calculate(data):
    """
    计算利息保障倍数

    公式: 利息保障倍数 = 经营利润 / 利息支出
    用于评估企业偿还利息的能力，值越高说明偿债能力越强

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

    result = data["operating_profit"] / data["interest_expense"].replace(0, float('nan'))
    return result
