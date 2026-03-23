
REQUIRED_FIELDS = ["basic_eps", "book_value_per_share", "close"]

def calculate(data, config):
    import pandas as pd
    eps = data["basic_eps"]
    bps = data["book_value_per_share"]
    close = data["close"]
    graham_value = (22.5 * eps * bps) ** 0.5
    margin_of_safety = (graham_value - close) / graham_value
    return pd.Series({
        "graham_value": graham_value,
        "current_price": close,
        "margin_of_safety": margin_of_safety,
    })
