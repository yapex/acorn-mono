"""
FCF 稳定性分析计算器
基于历年 FCF 计算均值、标准差、正值率、趋势等稳定性指标
"""

REQUIRED_FIELDS = ["free_cash_flow"]
SUPPORTED_MARKETS = ["A", "HK", "US"]

def calculate(data):
    """
    计算 FCF 稳定性分析指标

    输出:
    - fcf_mean: 历年 FCF 均值
    - fcf_std: 历年 FCF 标准差
    - fcf_cv: 变异系数 (std/mean，越小越稳定)
    - fcf_positive_years: FCF 为正的年数
    - fcf_total_years: 有效数据年数
    - fcf_positive_rate: 正值率 (正年数/总年数)
    - fcf_min: 历年最小值
    - fcf_max: 历年最大值

    Args:
        data: dict[str, pd.Series] - 字段数据

    Returns:
        pd.Series - 稳定性指标
    """
    import pandas as pd

    for field in REQUIRED_FIELDS:
        if field not in data:
            return pd.Series(dtype=float)
        if data[field].isna().all():
            return pd.Series(dtype=float)

    fcf = data["free_cash_flow"].dropna()
    total_years = len(fcf)

    if total_years == 0:
        return pd.Series(dtype=float)

    mean = fcf.mean()
    std = fcf.std()
    positive_years = (fcf > 0).sum()

    cv = std / mean if mean != 0 else float('nan')

    return pd.Series({
        "fcf_mean": mean,
        "fcf_std": std,
        "fcf_cv": cv,
        "fcf_positive_years": int(positive_years),
        "fcf_total_years": int(total_years),
        "fcf_positive_rate": positive_years / total_years,
        "fcf_min": fcf.min(),
        "fcf_max": fcf.max(),
    })
