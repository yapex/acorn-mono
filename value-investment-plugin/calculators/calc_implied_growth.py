"""Implied Growth Rate Calculator based on DCF model

Based on DCF model, calculate implied annual growth rate from current market cap.
"""
from typing import Any

# 依赖字段
required_fields = [
    "operating_cash_flow",
    "market_cap",
]

# 可选配置参数
optional_config = {
    "wacc": 0.10,        # 加权平均资本成本
    "g_terminal": 0.03, # 永续增长率
    "n_years": 10,       # 预测期
}


def calculate(results: dict[str, dict[int, Any]], config: dict = None) -> dict[int, float]:
    """计算隐含增长率

    Args:
        results: {field: {year: value}}
        config: 可选配置 {wacc, g_terminal, n_years}

    Returns:
        {year: implied_growth_rate}
    """
    # 合并默认配置
    cfg = {**optional_config, **(config or {})}
    wacc = cfg["wacc"]
    g_terminal = cfg["g_terminal"]
    n_years = cfg["n_years"]

    # 获取 FCF
    fcf_data, is_approximated = _get_fcf(results)
    if not fcf_data:
        return {}

    # 获取市值
    market_cap_data: dict[int, Any] = results.get("market_cap", {})
    if not market_cap_data:
        return {}

    # 计算隐含增长率
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


def _get_fcf(results: dict[str, dict[int, Any]]) -> tuple[dict[int, float], bool]:
    """获取自由现金流数据"""
    # 优先使用 free_cash_flow
    if "free_cash_flow" in results:
        fcf_data = results["free_cash_flow"]
        return {year: val for year, val in fcf_data.items() if val > 0}, False

    # 获取 OCF 和 CAPEX
    ocf_data = results.get("operating_cash_flow", {})
    capex_data = results.get("capital_expenditure", {})

    if not capex_data:
        return {year: val for year, val in ocf_data.items() if val > 0}, True

    fcf_data = {}
    for year in ocf_data:
        ocf = ocf_data.get(year, 0)
        capex = capex_data.get(year, 0)
        fcf = ocf - capex
        if fcf > 0:
            fcf_data[year] = fcf

    return fcf_data, False


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

    # 二分搜索 [-5%, 30%]
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
