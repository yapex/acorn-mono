"""Implied Growth Rate Calculator

基于 DCF 模型，用市值反推隐含的年增长率。
"""
from typing import Any

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
    results: dict[str, dict[int, Any]],
    config: dict[str, Any] | None = None,
) -> dict[str | int, float]:
    """计算隐含增长率"""
    cfg = {**DEFAULT_CONFIG, **(config or {})}
    wacc = cfg["wacc"]
    g_terminal = cfg["g_terminal"]
    n_years = cfg["n_years"]

    fcf_data = _get_fcf(results)
    if not fcf_data:
        return {}

    market_cap_data = results.get("market_cap", {})
    if not market_cap_data:
        return {}

    # 处理 market_cap 可能是单个值的情况
    if isinstance(market_cap_data, (int, float)):
        # 当前市值（单个值），用于最新年份计算
        # Tushare 返回的是万元，需要转换为元
        current_market_cap = float(market_cap_data) * 10000
        # 获取最新年份
        latest_year = max(fcf_data.keys()) if fcf_data else None
        if latest_year and current_market_cap > 0:
            fcf = fcf_data.get(latest_year, 0)
            if fcf > 0:
                g = _calculate_implied_growth(fcf, current_market_cap, wacc, g_terminal, n_years)
                if g is not None:
                    return {"current": g}
        return {}

    implied_growth = {}
    for year, fcf in fcf_data.items():
        if fcf <= 0:
            continue

        market_cap = market_cap_data.get(year)
        if not market_cap or market_cap <= 0:
            continue

        g = _calculate_implied_growth(fcf, market_cap, wacc, g_terminal, n_years)
        if g is not None:
            implied_growth[year] = g

    return implied_growth


def _get_fcf(results: dict[str, dict[int, Any]]) -> dict[int, float]:
    """获取自由现金流数据"""
    if "free_cash_flow" in results:
        return {y: v for y, v in results["free_cash_flow"].items() if v > 0}

    ocf = results.get("operating_cash_flow", {})
    capex = results.get("capital_expenditure", {})

    if not capex:
        return {y: v for y, v in ocf.items() if v > 0}

    return {y: ocf.get(y, 0) - capex.get(y, 0) for y in ocf if ocf.get(y, 0) - capex.get(y, 0) > 0}


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
