"""
ROCE 已动用资本回报率计算器
ROCE = EBIT / (总资产 - 流动负债) × 100%
反映企业对所有投入资本的利用效率，是衡量长期盈利能力的核心指标
"""

REQUIRED_FIELDS = ["operating_profit", "total_assets", "current_liabilities"]
SUPPORTED_MARKETS = ["A", "HK", "US"]

FORMAT_TYPE = "percent"

def calculate(data):
    """
    计算 ROCE（已动用资本回报率）

    公式: ROCE = EBIT / Capital Employed × 100%
          Capital Employed = 总资产 - 流动负债

    一般参考标准：
    - >15% 优秀，资本利用效率高
    - 10%-15% 良好
    - <10% 需关注，可能资本效率偏低
    - 长期稳定或上升的ROCE是竞争优势的信号

    Args:
        data: dict[str, pd.Series] - 字段数据

    Returns:
        pd.Series - 计算结果（百分比形式，如 15.11 表示 15.11%）
    """
    import pandas as pd

    for field in REQUIRED_FIELDS:
        if field not in data:
            return pd.Series(dtype=float)
        if data[field].isna().all():
            return pd.Series(dtype=float)

    capital_employed = data["total_assets"] - data["current_liabilities"]
    # 已动用资本为0或负值时无意义
    result = data["operating_profit"] / capital_employed.replace(0, float('nan')) * 100
    result = result.where(capital_employed > 0, float('nan'))
    return result
