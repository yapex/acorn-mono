"""
债务/EBITDA计算器
债务/EBITDA = 有息负债 / EBITDA
反映企业用EBITDA偿还全部债务所需的年数
"""

REQUIRED_FIELDS = ["interest_bearing_debt", "ebitda"]
SUPPORTED_MARKETS = ["A", "HK", "US"]

FORMAT_TYPE = "ratio"

def calculate(data):
    """
    计算债务/EBITDA比率

    公式: 债务/EBITDA = 有息负债 / EBITDA
    值越低说明偿债能力越强，通常<2为安全，>4为危险

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

    result = data["interest_bearing_debt"] / data["ebitda"].replace(0, float('nan'))
    # EBITDA 为负时比率无意义，置为 NaN
    result = result.where(data["ebitda"] > 0, float('nan'))
    return result
