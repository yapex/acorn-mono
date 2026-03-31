"""存货周转率计算器 = 营业成本 / 平均存货"""
SUPPORTED_MARKETS = ["A", "HK", "US"]
REQUIRED_FIELDS = ["operating_cost", "inventory"]

def calculate(data):
    import pandas as pd
    cost = data["operating_cost"]
    inv = data["inventory"]
    # 平均存货 = (本期存货 + 上期存货) / 2，首年无上期则用当年存货
    avg_inv = (inv + inv.shift(1)) / 2
    avg_inv.iloc[0] = inv.iloc[0]
    return cost / avg_inv.replace(0, float('nan'))
