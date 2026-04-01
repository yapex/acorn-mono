"""VI CLI - Value Investment Command Line Interface

通过 HTTP API 调用 vi_core 插件。
"""
from __future__ import annotations

import sys
from typing import Any

import typer

from acorn_cli.client import AcornClient  # type: ignore[import]

# Typer app
app = typer.Typer(help="Value Investment - 财务数据查询")


def _get_client() -> AcornClient:
    """获取 Acorn HTTP 客户端"""
    return AcornClient()


def _execute(command: str, args: dict[str, Any]) -> dict[str, Any]:
    """执行命令"""
    client = _get_client()
    return client.execute(command, args)


def _format_value(value: Any, field: str) -> str:
    """格式化单个值"""
    if value is None:
        return "N/A"

    if isinstance(value, float):
        # 百分比字段
        if field in ("roe", "roa", "gross_margin", "net_profit_margin", "current_ratio",
                     "quick_ratio", "debt_ratio", "cash_ratio", "ocf_to_debt",
                     "operating_profit_margin", "revenue_yoy", "net_profit_yoy",
                     "total_assets_yoy", "equity_yoy", "operating_cash_flow_yoy"):
            return f"{value:.2f}%"
        # 比率字段
        if field in ("pe_ratio", "pb_ratio"):
            return f"{value:.2f}"
        # 市值（亿元）
        if field == "market_cap":
            return f"{value/10000:.2f}亿"
        # 大数字
        if abs(value) >= 1e8:
            return f"{value/1e8:.2f}亿"
        elif abs(value) >= 1e4:
            return f"{value/1e4:.2f}万"
        else:
            return f"{value:.2f}"

    if isinstance(value, int):
        return str(value)

    return str(value)


def _print_table(data: dict[str, Any]) -> None:
    """打印表格"""
    if not data.get("data"):
        print("No data available")
        return

    data_fields = data.get("fields_fetched", list(data["data"].keys()))
    if not data_fields:
        print("No data available")
        return

    # 分离数据类型
    all_years: set[int] = set()
    time_series_data = {}
    single_values = {}
    calculator_results = []

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

    # 时间序列表格
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

            # 打印表格
            col_widths = [max(len(str(row[i])) for row in [headers] + rows) for i in range(len(headers))]
            header_line = " | ".join(str(h).ljust(col_widths[i]) for i, h in enumerate(headers))
            print(header_line)
            print("-" * len(header_line))
            for row in rows:
                print(" | ".join(str(v).ljust(col_widths[i]) for i, v in enumerate(row)))

    # 单值表格
    if single_values:
        print("\n市场数据:")
        for field, val in single_values.items():
            print(f"  {field}: {_format_value(val, field)}")

    # 计算器结果
    if calculator_results:
        print("\n计算器结果:")
        for field, values in calculator_results:
            for key, val in values.items():
                label = f"{field}" if len(values) == 1 else f"{field} ({key})"
                print(f"  {label}: {_format_value(val, field)}")


@app.command("query")
def query(
    symbol: str = typer.Argument(..., help="股票代码 (如 600519, AAPL)"),
    items: str = typer.Option("all", "-i", "--items", help="逗号分隔的数据项/计算器列表，或 'all'"),
    years: int = typer.Option(10, "-y", "--years", help="查询年数"),
    wacc: float = typer.Option(0.08, "--wacc", help="DCF 计算中的 WACC"),
    g_terminal: float = typer.Option(0.03, "--g-terminal", help="永续增长率"),
) -> None:
    """查询股票财务数据"""
    # 构建计算器配置
    calc_config: dict[str, Any] = {}
    if items != "all" and items:
        # 解析 items 中的计算器，注入默认配置
        for item in items.split(","):
            item = item.strip()
            if item == "implied_growth":
                calc_config[item] = {
                    "wacc": wacc,
                    "g_terminal": g_terminal,
                    "n_years": years,
                }

    try:
        result = _execute("vi_query", {
            "symbol": symbol,
            "items": items,
            "years": years,
            "calculator_config": calc_config,
        })

        if not result.get("success", False):
            print(f"错误：{result.get('error', {}).get('message', 'Unknown error')}", file=sys.stderr)
            raise typer.Exit(1)

        data = result.get("data", {})
        _print_table(data)

    except Exception as e:
        print(f"错误：{e}", file=sys.stderr)
        raise typer.Exit(1)


@app.command("list")
def list_items(
    category: str = typer.Option("all", "-c", "--category", help="类别：all, fields, calculators"),
    market: str = typer.Option(None, "-m", "--market", help="按市场过滤 (A, HK, US)"),
) -> None:
    """列出可用的字段和计算器"""
    try:
        if category in ("all", "fields"):
            args = {}
            if market:
                args["market"] = market
            result = _execute("vi_list_fields", args)
            if result.get("success", False):
                fields = result.get("data", {}).get("fields", [])
                market_label = f" ({market} 市场)" if market else ""
                print(f"\n可用字段{market_label} ({len(fields)}):\n")
                for f in sorted(fields):
                    print(f"  - {f}")
                print()

        if category in ("all", "calculators"):
            result = _execute("vi_list_calculators", {})
            if result.get("success", False):
                calcs = result.get("data", {}).get("calculators", [])
                print(f"\n可用计算器 ({len(calcs)}):\n")
                for calc in calcs:
                    name = calc.get('name', 'unknown')
                    supported_markets = calc.get('supported_markets', [])
                    print(f"  {name}")
                    print(f"    市场：{', '.join(supported_markets)}")
                    print(f"    描述：{calc.get('description', 'N/A')}")
                    print(f"    必需字段：{', '.join(calc.get('required_fields', []))}")
                    print()

    except Exception as e:
        print(f"错误：{e}", file=sys.stderr)
        raise typer.Exit(1)


@app.command("reload")
def reload(
    name: str = typer.Argument(None, help="计算器名称（省略则全部重载）"),
) -> None:
    """重新加载计算器（热加载，无需重启 agent）"""
    try:
        args = {}
        if name:
            args["name"] = name
        result = _execute("vi_reload_calculator", args)
        if result.get("success", False):
            data = result.get("data", {})
            total = data.get("total", "?")
            file_based = data.get("file_based", "?")
            dynamic = data.get("dynamic", "?")
            if name:
                print(f"✅ 计算器 '{name}' 已重载")
            else:
                print(f"✅ 已重载全部计算器 (共 {total} 个：文件 {file_based} + 动态 {dynamic})")
        else:
            print(f"❌ 重载失败", file=sys.stderr)
            raise typer.Exit(1)
    except typer.Exit:
        raise
    except Exception as e:
        print(f"错误：{e}", file=sys.stderr)
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
