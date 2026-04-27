"""PE历史估值百分位分析

计算当前PE在历史每日PE中的百分位分布。
PE = 当日不复权收盘价 / 最新可获得的年度基本EPS(按fiscal_year)。
"""

REQUIRED_FIELDS = ["basic_eps"]
DAILY_FIELDS = ["close"]

FORMAT_TYPES = {
    "pe_current": "market",
    "pe_median": "market",
    "pe_p25": "market",
    "pe_p75": "market",
    "pe_current_percentile": "percentage",
}


def calculate(data):
    """
    Args:
        data: {
            "basic_eps": pd.Series(index=fiscal_year, values=eps),
            "close": pd.DataFrame(date, close),  # 框架自动注入每日数据
        }

    Returns:
        {"values": pd.Series({...}), "format_types": {...}}
    """
    import pandas as pd
    import numpy as np

    eps_series = data["basic_eps"].dropna()
    close_df = data.get("close")

    if eps_series.empty or close_df is None or close_df.empty:
        return {"values": pd.Series(dtype=float), "format_types": FORMAT_TYPES}

    # 确保日期列
    if "date" in close_df.columns:
        close_df = close_df.copy()
        close_df["date"] = pd.to_datetime(close_df["date"])
    else:
        return {"values": pd.Series(dtype=float), "format_types": FORMAT_TYPES}

    # 构建 EPS 查找表: fiscal_year -> eps
    # 每个交易日使用当时最新可用的 EPS:
    #   fiscal_year=N 的 EPS, 从 N+1 年 1 月 1 日起视为可用
    eps_lookup = {}
    for year, eps in eps_series.items():
        eps_lookup[int(year)] = float(eps)

    # 按年份降序排列的可用年份列表
    available_years = sorted(eps_lookup.keys(), reverse=True)

    if not available_years:
        return {"values": pd.Series(dtype=float), "format_types": FORMAT_TYPES}

    # 对每个交易日计算 PE
    pe_values = []
    for _, row in close_df.iterrows():
        trade_date = row["date"]
        close_price = row["close"]

        if pd.isna(close_price) or close_price <= 0:
            continue

        # 找到交易日期时可用的最新 fiscal_year EPS
        trade_year = trade_date.year
        best_eps = None
        for fy in available_years:
            # fiscal_year=fy 的 EPS 从 fy+1 年 1 月 1 日起可用
            if trade_year >= fy + 1:
                best_eps = eps_lookup[fy]
                break

        if best_eps is None or best_eps <= 0:
            continue

        pe_values.append({
            "date": trade_date,
            "pe": close_price / best_eps,
        })

    if not pe_values:
        return {"values": pd.Series(dtype=float), "format_types": FORMAT_TYPES}

    pe_df = pd.DataFrame(pe_values)
    pe_series = pe_df["pe"]

    current_pe = pe_series.iloc[-1]
    median_pe = pe_series.median()
    p25 = pe_series.quantile(0.25)
    p75 = pe_series.quantile(0.75)

    # 当前 PE 在历史中的百分位
    from scipy import stats
    current_percentile = stats.percentileofscore(pe_series.values, current_pe)

    return {
        "values": pd.Series({
            "pe_current": current_pe,
            "pe_median": median_pe,
            "pe_p25": p25,
            "pe_p75": p75,
            "pe_current_percentile": current_percentile,
        }),
        "format_types": FORMAT_TYPES,
    }
