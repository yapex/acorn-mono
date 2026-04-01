
REQUIRED_FIELDS = ["basic_eps", "book_value_per_share", "close"]

# 多指标: 每个 metric 独立声明 format_type
FORMAT_TYPES = {
    "graham_value": "market",
    "current_price": "market",
    "margin_of_safety": "percentage",
}

def calculate(data):
    import pandas as pd
    eps = data["basic_eps"]
    bps = data["book_value_per_share"]
    close = data["close"]
    graham_value = (22.5 * eps * bps) ** 0.5
    margin_of_safety = (graham_value - close) / graham_value
    return {
        "values": pd.Series({
            "graham_value": graham_value,
            "current_price": close,
            "margin_of_safety": margin_of_safety,
        }),
        "format_types": {
            "graham_value": "market",
            "current_price": "market",
            "margin_of_safety": "percentage",
        },
    }
