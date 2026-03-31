"""
自由现金流计算器
FCF = 经营活动现金流量净额 - 资本支出
"""

REQUIRED_FIELDS = ["operating_cash_flow", "capital_expenditure"]
MARKET_CODES = ["HK", "US"]

def calculate(data):
    """
    计算自由现金流 (Free Cash Flow)

    公式: FCF = 经营活动现金流量净额 - 资本支出

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

    result = data["operating_cash_flow"] - data["capital_expenditure"]
    return result
