"""Output formatting utilities for acorn-agent CLI"""
from __future__ import annotations

import json
from typing import Any

from tabulate import tabulate


def _format_value(value: Any, field: str) -> str:
    """Format a single value"""
    if value is None:
        return "N/A"

    if isinstance(value, float):
        # Percentage fields
        if field in (
            "roe", "roa", "gross_margin", "net_profit_margin", "current_ratio",
            "quick_ratio", "debt_ratio", "cash_ratio", "ocf_to_debt",
            "operating_profit_margin", "revenue_yoy", "net_profit_yoy",
            "total_assets_yoy", "equity_yoy", "operating_cash_flow_yoy",
        ):
            return f"{value:.2f}%"
        # Ratio fields (pe, pb)
        if field in ("pe_ratio", "pb_ratio"):
            return f"{value:.2f}"
        # Market cap (in 亿元)
        if field == "market_cap":
            return f"{value/10000:.2f}亿"
        # Large numbers
        if abs(value) >= 1e8:
            return f"{value/1e8:.2f}亿"
        elif abs(value) >= 1e4:
            return f"{value/1e4:.2f}万"
        else:
            return f"{value:.2f}"

    if isinstance(value, int):
        return str(value)

    return str(value)


def _format_output(data: dict[str, Any], fmt: str) -> str:
    """Format query result"""
    if fmt == "json":
        return json.dumps(data, indent=2, ensure_ascii=False, default=str)

    if not data.get("data"):
        return "No data available"

    data_fields = data.get("fields_fetched", list(data["data"].keys()))
    if not data_fields:
        return "No data available"

    # Separate data types
    all_years: set[int] = set()
    time_series_data: dict[str, dict] = {}  # {field: {year: value}}
    calculator_results: list[tuple[str, dict]] = []  # [(field, {key: value})]

    for field in data_fields:
        field_data = data["data"][field]
        if isinstance(field_data, dict):
            # Support both int and string year keys
            year_keys = [k for k in field_data.keys() if isinstance(k, (int, str)) and str(k).isdigit()]
            if year_keys:
                # Convert string years to int for consistency
                int_years = {int(k): v for k, v in field_data.items() if str(k).isdigit()}
                all_years.update(int_years.keys())
                time_series_data[field] = int_years
            else:
                calculator_results.append((field, field_data))

    output_parts = []

    # Time series table
    if time_series_data:
        if all_years:
            headers = ["Field"] + [str(y) for y in sorted(all_years, reverse=True)]
            rows = []
            for field in time_series_data:
                field_data = time_series_data[field]
                row = [field] + [
                    _format_value(field_data.get(y), field)
                    for y in sorted(all_years, reverse=True)
                ]
                rows.append(row)
            output_parts.append(tabulate(rows, headers=headers, tablefmt="grid"))

    # Calculator results
    if calculator_results:
        calc_table = []
        for field, values in calculator_results:
            for key, val in values.items():
                label = f"{field}" if len(values) == 1 else f"{field} ({key})"
                calc_table.append([label, _format_value(val, field)])
        output_parts.append(tabulate(calc_table, headers=["Calculator", "Value"], tablefmt="grid"))

    return "\n\n".join(output_parts) if output_parts else "No data available"
