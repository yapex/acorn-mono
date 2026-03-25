"""老唐估值法

基于唐朝《手把手教你读财报》的估值方法：
1. 计算最近5年净利润年化增长率
2. 预估3年后净利润
3. 合理市值 = 3年后净利润 × 25倍PE
4. 理想买入价 = 合理市值 × 50%
5. 卖出价 = 合理市值 × 200%

输出每股价格，方便直接对比当前股价。
"""
from typing import Any

import pandas as pd

REQUIRED_FIELDS = [
    "net_profit",
    "basic_eps",
    "close",
]

# 字段别名：优先使用主字段，如果不存在则尝试别名
FIELD_ALIASES = {
    "net_profit": ["parent_net_profit"],  # 港股用 parent_net_profit
}

DEFAULT_CONFIG = {
    "pe_ratio": 25,          # 合理PE倍数
    "buy_ratio": 0.50,       # 买入折扣（合理市值的50%）
    "sell_ratio": 2.00,      # 卖出倍数（合理市值的200%）
    "min_years": 5,          # 计算CAGR所需最小年数
}


def calculate(
    data: dict[str, pd.Series],
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """计算老唐估值
    
    Args:
        data: dict[str, pd.Series]，字段名 -> Series(index=年份)
        config: Calculator configuration
        
    Returns:
        dict 包含：
        - cagr: 年化增长率
        - current_eps: 当前每股收益
        - eps_3y_later: 3年后预估每股收益
        - buy_price: 理想买入价（每股）
        - sell_price: 卖出价（每股）
        - current_price: 当前股价
        - margin_of_safety: 安全边际 (当前股价 vs 买入价)
    """
    cfg = {**DEFAULT_CONFIG, **(config or {})}
    pe_ratio = cfg["pe_ratio"]
    buy_ratio = cfg["buy_ratio"]
    sell_ratio = cfg["sell_ratio"]
    min_years = cfg["min_years"]
    
    # 解析字段别名
    def get_field(field_name: str) -> pd.Series | None:
        """获取字段数据，支持别名"""
        if field_name in data and data[field_name] is not None:
            return data[field_name]
        # 尝试别名
        for alias in FIELD_ALIASES.get(field_name, []):
            if alias in data and data[alias] is not None:
                return data[alias]
        return None
    
    # 检查必需字段
    profit_series = get_field("net_profit")
    eps_series = get_field("basic_eps")
    close_series = get_field("close")
    
    if profit_series is None or eps_series is None or close_series is None:
        return {}
    
    profit_series = profit_series.dropna()
    eps_series = eps_series.dropna()
    close_series = close_series.dropna()
    
    if profit_series.empty or eps_series.empty or close_series.empty:
        return {}
    
    # 按年份排序（升序，最早的在前）
    profit_series = profit_series.sort_index()
    
    # 需要至少 min_years 年的数据计算 CAGR
    if len(profit_series) < min_years:
        return {}
    
    # 取最近 min_years 年的数据
    recent_profits = profit_series.tail(min_years)
    
    # 计算年化增长率 (CAGR)
    first_year = recent_profits.index[0]
    last_year = recent_profits.index[-1]
    first_profit = recent_profits.iloc[0]
    last_profit = recent_profits.iloc[-1]
    
    years = int(last_year) - int(first_year)
    if years <= 0 or first_profit <= 0:
        return {}
    
    cagr = (last_profit / first_profit) ** (1 / years) - 1
    
    # 如果增长率为负，限制在 -10% 到 50% 之间
    cagr = max(-0.10, min(0.50, cagr))
    
    # 获取最新年份的 EPS 和股价
    last_year_int = int(last_year)
    if last_year_int not in eps_series.index or last_year_int not in close_series.index:
        # 尝试获取最新的 EPS 和 close
        current_eps = float(eps_series.iloc[-1])
        current_price = float(close_series.iloc[-1])
    else:
        current_eps = float(eps_series.loc[last_year_int])
        current_price = float(close_series.loc[last_year_int])
    
    # 计算3年后的预估 EPS（假设 EPS 增长率与净利润相同）
    eps_3y_later = current_eps * ((1 + cagr) ** 3)
    
    # 计算每股价格
    fair_price_per_share = eps_3y_later * pe_ratio      # 合理股价
    buy_price_per_share = fair_price_per_share * buy_ratio   # 买入价
    sell_price_per_share = fair_price_per_share * sell_ratio  # 卖出价
    
    # 与理想买入价的差距
    # 正值 = 当前股价低于买入价，可以买入
    # 负值 = 当前股价高于买入价，需要等待
    if current_price > 0:
        gap = (buy_price_per_share - current_price) / current_price * 100
    else:
        gap = 0
    
    return {
        last_year_int: {
            # 核心输出
            "buy_price": round(buy_price_per_share, 2),      # 理想买入价（每股）
            "sell_price": round(sell_price_per_share, 2),    # 卖出价（每股）
            "current_price": round(current_price, 2),        # 当前股价
            "gap": round(gap, 1),                            # 与买入价差距 (%)
            
            # 详细信息
            "cagr": round(cagr, 4),
            "current_eps": round(current_eps, 2),
            "eps_3y_later": round(eps_3y_later, 2),
            "fair_price": round(fair_price_per_share, 2),    # 合理股价
            
            # 市值信息（参考）
            "current_profit": round(float(last_profit), 2),
            "profit_3y_later": round(float(last_profit * ((1 + cagr) ** 3)), 2),
            
            # 计算依据
            "years_used": min_years,
            "first_year": int(first_year),
            "last_year": last_year_int,
        }
    }