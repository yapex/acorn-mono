"""
VI CLI Commands
===============

CLI commands for Value Investment plugin.
Loaded dynamically via acorn.cli.commands entry point.
"""

from typing import Optional

import typer

app = typer.Typer(name="vi", help="Value Investment - 财务数据查询")


@app.command()
def query(
    symbol: str,
    years: int = 10,
    fields: Optional[str] = None,
    calculators: Optional[str] = None,
):
    """查询股票财务数据

    Args:
        symbol: 股票代码 (如 600519)
        years: 查询年份数
        fields: 字段列表 (逗号分隔)
        calculators: 计算器列表 (逗号分隔)
    """
    from acorn_core import Task, Acorn

    acorn = Acorn()
    acorn.load_plugins()

    task = Task(command="vi_query", args={
        "symbol": symbol,
        "years": years,
        "fields": fields,
        "calculators": calculators,
    })
    response = acorn.execute(task)

    if response.success:
        typer.echo(f"✓ Query successful: {response.data}")
    else:
        typer.echo(f"✗ Error: {response.error.message}")


@app.command("list-fields")
def list_fields(
    source: Optional[str] = None,
    prefix: Optional[str] = None,
):
    """列出可用字段

    Args:
        source: 数据源 (可选)
        prefix: 字段前缀过滤 (可选)
    """
    from acorn_core import Task, Acorn

    acorn = Acorn()
    acorn.load_plugins()

    task = Task(command="vi_list_fields", args={
        "source": source,
        "prefix": prefix,
    })
    response = acorn.execute(task)

    if response.success:
        data = response.data or {}
        fields = data.get("fields", []) if isinstance(data, dict) else data
        if fields:
            for field in fields:
                typer.echo(f"  • {field}")
        else:
            typer.echo("No fields found")
    else:
        typer.echo(f"✗ Error: {response.error.message}")


@app.command("list-calculators")
def list_calculators():
    """列出可用计算器"""
    from acorn_core import Task, Acorn

    acorn = Acorn()
    acorn.load_plugins()

    task = Task(command="vi_list_calculators", args={})
    response = acorn.execute(task)

    if response.success:
        calcs = response.data or []
        if calcs:
            for calc in calcs:
                typer.echo(f"  • {calc}")
        else:
            typer.echo("No calculators found")
    else:
        typer.echo(f"✗ Error: {response.error.message}")
