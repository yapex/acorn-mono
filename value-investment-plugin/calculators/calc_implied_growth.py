"""Implied Growth Rate Calculator

基于 DCF 模型，用市值反推隐含的年增长率。

输入数据格式：dict[str, pd.Series]
- key: 字段名 (operating_cash_flow, market_cap 等)
- value: pd.Series，index=年份, values=数值
"""
from typing import Any

import pandas as pd

REQUIRED_FIELDS = [
    "operating_cash_flow",
    "market_cap",
]

DEFAULT_CONFIG = {
    "wacc": 0.10,
    "g_terminal": 0.03,
    "n_years": 10,
}


def calculate(
    data: dict[str, pd.Series],
    config: dict[str, Any] | None = None,
) -> pd.Series:
    """计算隐含增长率
    
    Args:
        data: dict[str, pd.Series]，字段名 -> Series(index=年份)
        config: Calculator configuration
        
    Returns:
        pd.Series with implied growth rates, index=年份
    """
    cfg = {**DEFAULT_CONFIG, **(config or {})}
    wacc = cfg["wacc"]
    g_terminal = cfg["g_terminal"]
    n_years = cfg["n_years"]

    if not data:
        return pd.Series(dtype=float)

    # 获取 FCF 数据
    fcf_series = _get_fcf(data)
    if fcf_series.empty:
        return pd.Series(dtype=float)

    # 获取市值数据
    if "market_cap" not in data:
        return pd.Series(dtype=float)
    
    market_cap_series = data["market_cap"]
    
    # 处理市值可能是单个值的情况（广播到所有年份）
    if len(market_cap_series) == 1:
        # 单个市值，广播到所有年份
        current_market_cap = float(market_cap_series.iloc[0])
        if current_market_cap <= 0:
            return pd.Series(dtype=float)
        market_cap_series = pd.Series(
            {year: current_market_cap for year in fcf_series.index},
            index=fcf_series.index
        )
    
    # 规范化市值单位（万元 -> 元）
    market_cap_series = _normalize_market_cap(market_cap_series, fcf_series)

    result = pd.Series(dtype=float)
    
    for year in fcf_series.index:
        fcf = fcf_series.loc[year]
        market_cap = market_cap_series.loc[year] if year in market_cap_series.index else market_cap_series.iloc[0]
        
        if fcf <= 0 or pd.isna(market_cap) or market_cap <= 0:
            continue
        
        g = _calculate_implied_growth(fcf, market_cap, wacc, g_terminal, n_years)
        if g is not None:
            result.loc[year] = g

    return result


def _get_fcf(data: dict[str, pd.Series]) -> pd.Series:
    """获取自由现金流数据"""
    if "free_cash_flow" in data:
        return data["free_cash_flow"].dropna().loc[lambda x: x > 0]
    
    if "operating_cash_flow" not in data:
        return pd.Series(dtype=float)
    
    ocf = data["operating_cash_flow"]
    
    if "capital_expenditure" not in data:
        return ocf.dropna().loc[lambda x: x > 0]
    
    capex = data["capital_expenditure"]
    # 确保 capex 和 ocf 有相同的 index
    common_idx = ocf.index.intersection(capex.index)
    fcf = ocf.reindex(common_idx) - capex.reindex(common_idx).fillna(0)
    return fcf.dropna().loc[lambda x: x > 0]


def _normalize_market_cap(market_cap: pd.Series, fcf: pd.Series) -> pd.Series:
    """规范化市值单位
    
    Tushare 返回的市值单位是万元，需要转换为元。
    如果市值明显小于 OCF（正常情况下市值 > OCF），则说明单位是万元。
    """
    if market_cap.empty or fcf.empty:
        return market_cap
    
    # 获取市值和 OCF 的中位数进行比较
    cap_median = market_cap.median()
    fcf_median = fcf.median()
    
    # 如果市值中位数小于 OCF 中位数，说明市值是万元单位
    # 正常情况下市值 > OCF（比如 10-50 倍）
    if cap_median < fcf_median:
        # 市值是万元，转为元
        return market_cap * 10000
    
    return market_cap


def _calculate_implied_growth(
    current_fcf: float,
    market_cap: float,
    wacc: float,
    g_terminal: float,
    n_years: int,
) -> float | None:
    """使用二分搜索计算隐含增长率"""

    def dcf_value(g: float) -> float:
        if g >= wacc:
            return float("inf")
        if g <= -0.1:
            return 0.0

        projected_fcf = [current_fcf * ((1 + g) ** i) for i in range(1, n_years + 1)]
        tv = (projected_fcf[-1] * (1 + g_terminal)) / (wacc - g_terminal)

        pv = sum(fc / ((1 + wacc) ** i) for i, fc in enumerate(projected_fcf, 1))
        pv += tv / ((1 + wacc) ** n_years)

        return pv

    low, high = -0.05, 0.30
    tolerance = 0.0001

    for _ in range(100):
        mid = (low + high) / 2
        pv = dcf_value(mid)

        if abs(pv - market_cap) / market_cap < tolerance:
            return mid

        if pv > market_cap:
            high = mid
        else:
            low = mid

    return (low + high) / 2
