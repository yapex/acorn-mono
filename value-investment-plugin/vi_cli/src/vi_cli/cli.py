"""VI CLI - Value Investment Command Line Interface

Usage:
    v-invest query <symbol> [-r <fields>] [-y <years>] [--format <format>]
    v-invest list-fields [--source <source>] [--prefix <prefix>]
    v-invest list-calculators
"""
from __future__ import annotations

import os
import sys
from importlib.metadata import entry_points
from pathlib import Path
from typing import TYPE_CHECKING, Any

# Third-party imports (installed via uv)
import pluggy  # type: ignore[import]
import typer  # type: ignore[import]
from tabulate import tabulate  # type: ignore[import]

# Add plugin paths for local packages
_plugin_paths = [
    Path(__file__).parent.parent.parent.parent / "vi_core" / "src",
    Path(__file__).parent.parent.parent.parent / "vi_fields_ifrs" / "src",
    Path(__file__).parent.parent.parent.parent / "vi_fields_extension" / "src",
    Path(__file__).parent.parent.parent.parent / "provider_tushare" / "src",
    Path(__file__).parent.parent.parent.parent / "calculators",
]

for _p in _plugin_paths:
    if str(_p) not in sys.path and _p.exists():
        sys.path.insert(0, str(_p))

# Local package imports
from vi_core import ValueInvestmentSpecs, plugin as vi_core_plugin  # type: ignore[import]
from vi_core.spec import CalculatorSpec  # type: ignore[import]


def _get_entry_points(group: str):
    """Get entry points by group, compatible with Python 3.9-3.12"""
    try:
        # Python 3.10+
        return entry_points(group=group)
    except TypeError:
        # Python 3.9
        eps = entry_points()
        if hasattr(eps, "select"):
            return eps.select(group=group)
        elif isinstance(eps, dict):
            return eps.get(group, [])
        return []

# Load calculators via entry_points
_calculator_entry_points = [
    ("calculators", "calc_implied_growth"),
]


def _setup_plugins() -> Any:
    """Setup pluggy plugin manager and register all plugins"""
    # Import calculator loader
    from vi_calculators import CalculatorLoaderPlugin  # type: ignore[import]

    pm = pluggy.PluginManager("value_investment")
    pm.add_hookspecs(ValueInvestmentSpecs)

    # Register core plugin
    pm.register(vi_core_plugin, name="vi_core")

    # Register calculator loader
    calc_loader = CalculatorLoaderPlugin()
    pm.register(calc_loader, name="calculators")

    # Register providers and fields via entry_points
    _entry_point_configs = [
        ("value_investment.providers", "tushare"),
        ("value_investment.fields", "ifrs"),
        ("value_investment.fields", "extension"),
    ]

    for group, name in _entry_point_configs:
        eps = _get_entry_points(group)
        for ep in eps:
            if ep.name == name:
                try:
                    plugin_instance = ep.load()
                    pm.register(plugin_instance, name=ep.name)
                except Exception as e:
                    print(f"Warning: Failed to load {name}: {e}", file=sys.stderr)

    # Set plugin manager for vi_core
    vi_core_plugin.set_plugin_manager(pm)

    return pm


# Initialize plugin manager once
_pm = _setup_plugins()

# Typer app
app = typer.Typer(help="Value Investment CLI - Financial Data Analysis")


def _format_output(data: dict[str, Any], fmt: str) -> str:
    """Format query result"""
    if fmt == "json":
        import json
        return json.dumps(data, indent=2, ensure_ascii=False, default=str)

    if not data.get("data"):
        return "No data available"

    data_fields = data.get("fields_fetched", list(data["data"].keys()))
    if not data_fields:
        return "No data available"

    # Separate data types
    all_years: set[int] = set()
    time_series_data = {}  # {field: {year: value}}
    single_values = {}  # {field: value}
    calculator_results = []  # [(field, {key: value})]

    for field in data_fields:
        field_data = data["data"][field]
        if isinstance(field_data, dict):
            year_keys = [k for k in field_data.keys() if isinstance(k, int)]
            if year_keys:
                all_years.update(year_keys)
                time_series_data[field] = field_data
            else:
                calculator_results.append((field, field_data))
        else:
            single_values[field] = field_data

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

    # Single value table (market data)
    if single_values:
        headers = ["Field", "Value"]
        rows = [[field, _format_value(val, field)] for field, val in single_values.items()]
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


def _format_value(value: Any, field: str) -> str:
    """Format a single value"""
    if value is None:
        return "N/A"

    if isinstance(value, float):
        # Percentage fields
        if field in ("roe", "roa", "gross_margin", "net_profit_margin", "current_ratio",
                     "quick_ratio", "debt_ratio", "cash_ratio", "ocf_to_debt",
                     "operating_profit_margin", "revenue_yoy", "net_profit_yoy",
                     "total_assets_yoy", "equity_yoy", "operating_cash_flow_yoy"):
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


@app.command()
def query(
    symbol: str = typer.Argument(..., help="Stock symbol (e.g. 600519, 000001)"),
    fields: str = typer.Option("all", "-r", "--fields", help="Comma-separated fields"),
    years: int = typer.Option(10, "-y", "--years", help="Number of years"),
    format: str = typer.Option("table", "--format", help="Output format: table, markdown, json"),
    calculators: str = typer.Option("", "-c", "--calculators", help="Calculators to run"),
    wacc: float = typer.Option(0.08, "--wacc", help="WACC for DCF calculations"),
    g_terminal: float = typer.Option(0.03, "--g-terminal", help="Terminal growth rate"),
) -> None:
    """Query financial data for a stock"""
    # Parse calculators config
    calc_config: dict[str, Any] = {}
    if calculators:
        for calc in calculators.split(","):
            calc = calc.strip()
            if calc == "implied_growth":
                calc_config[calc] = {
                    "wacc": wacc,
                    "g_terminal": g_terminal,
                    "n_years": years,
                }

    # Build calculator config dict
    calc_config_dict = {"calculator_config": calc_config}

    # Build calculators string
    calc_str = calculators

    # Execute query
    result = _pm.hook.vi_handle(
        command="query",
        args={
            "symbol": symbol,
            "fields": fields,
            "years": years,
            "calculators": calc_str,
            "calculator_config": calc_config,
        },
    )

    if not result.get("success", False):
        print(f"Error: {result.get('error', 'Unknown error')}", file=sys.stderr)
        raise typer.Exit(1)

    output_data = result.get("data", {})

    # Select format
    fmt = format.lower()
    if fmt == "table":
        fmt = "grid"

    print(f"\n=== {symbol} 查询结果 ===")
    print(f"字段: {fields}")
    print(f"年份范围: {output_data.get('end_year', 'N/A') - years + 1} - {output_data.get('end_year', 'N/A')}")
    print()

    print(_format_output(output_data, fmt))


@app.command()
def list_fields(
    source: str | None = typer.Option(None, "--source", help="Filter by source"),
    prefix: str | None = typer.Option(None, "--prefix", help="Filter by prefix"),
) -> None:
    """List all available fields"""
    result = _pm.hook.vi_handle(
        command="list_fields",
        args={"source": source, "prefix": prefix},
    )

    if not result.get("success", False):
        print(f"Error: {result.get('error', 'Unknown error')}", file=sys.stderr)
        raise typer.Exit(1)

    fields_data = result.get("data", {})
    fields = fields_data.get("fields", [])
    by_source = fields_data.get("by_source", {})

    print(f"\n可用字段 ({len(fields)}):\n")

    if by_source:
        # Group by source
        by_src: dict[str, list[str]] = {}
        for f in fields:
            src = by_source.get(f, "unknown")
            if src not in by_src:
                by_src[src] = []
            by_src[src].append(f)

        for src, fs in sorted(by_src.items()):
            print(f"  [{src}]")
            for f in fs:
                print(f"    - {f}")
            print()
    else:
        for f in fields:
            print(f"  - {f}")


@app.command()
def list_calculators() -> None:
    """List all available calculators"""
    calcs = _pm.hook.vi_list_calculators()

    # Flatten if nested
    if calcs and isinstance(calcs[0], list):
        calcs = calcs[0]

    print(f"\n可用计算器 ({len(calcs)}):\n")

    for calc in calcs:
        print(f"  {calc.get('name', 'unknown')}")
        print(f"    描述: {calc.get('description', 'N/A')}")
        print(f"    必需字段: {', '.join(calc.get('required_fields', []))}")
        print()


if __name__ == "__main__":
    app()
