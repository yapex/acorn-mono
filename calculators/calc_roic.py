"""
投入资本回报率计算器（美股）
ROIC = 税后营业利润 / 投入资本
投入资本 = 股东权益合计 + 短期债务 + 长期负债
"""

REQUIRED_FIELDS = ["operating_profit", "income_tax", "total_equity", "short_term_debt", "long_term_debt"]
MARKET_CODES = ["US"]

def calculate(data):
    """
    计算投入资本回报率

    公式: ROIC = NOPAT / Invested Capital
    NOPAT = 营业利润 * (1 - 有效税率)
    有效税率 = 所得税 / (营业利润 + 所得税)
    Invested Capital = 股东权益合计 + 短期债务 + 长期负债

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

    # 有效税率 = 所得税 / 税前利润(营业利润+所得税)
    pretax_profit = data["operating_profit"] + data["income_tax"]
    effective_tax_rate = data["income_tax"] / pretax_profit.replace(0, float('nan'))
    effective_tax_rate = effective_tax_rate.clip(lower=0, upper=1)

    # NOPAT = 营业利润 * (1 - 有效税率)
    nopat = data["operating_profit"] * (1 - effective_tax_rate)

    # 投入资本 = 股东权益 + 短期债务 + 长期负债
    invested_capital = data["total_equity"] + data["short_term_debt"] + data["long_term_debt"]

    result = nopat / invested_capital.replace(0, float('nan'))
    return result
