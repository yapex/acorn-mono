"""
Calculator: debt_to_ebitda
债务/EBITDA比率，用于评估偿债能力
"""
REQUIRED_FIELDS = ["interest_bearing_debt", "ebitda"]


def calculate(data, config):
    """
    Calculate debt_to_ebitda ratio

    Args:
        data: dict[str, pd.Series] - field data
        config: dict - user configuration

    Returns:
        pd.Series - debt_to_ebitda ratio with year as index
    """
    debt = data["interest_bearing_debt"]
    ebitda = data["ebitda"]

    # 避免除零
    result = debt / ebitda.replace(0, float("nan"))
    return result
