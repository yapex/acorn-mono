"""
VI CLI Commands
===============
CLI commands for Value Investment plugin.
通过 RPC 调用 acorn 服务执行命令。
"""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

import typer

app = typer.Typer(name="vi", help="Value Investment - 财务数据查询")


def _get_client():
    """获取 RPC 客户端"""
    from acorn_cli.client import AcornClient
    return AcornClient()


def _check_server_running() -> bool:
    """检查服务是否运行"""
    try:
        client = _get_client()
        result = client.health_check()
        return result.get("healthy", False)
    except Exception:
        return False


def _start_server_background() -> None:
    """后台启动服务"""
    venv_bin = Path(sys.executable).parent
    acorn_agent_script = venv_bin / "acorn-agent"

    subprocess.Popen(
        [str(acorn_agent_script)],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )


def _ensure_server_running() -> bool:
    """确保服务运行"""
    if _check_server_running():
        return True

    typer.echo("启动 acorn 服务...", err=True)
    _start_server_background()

    for _ in range(20):
        time.sleep(0.5)
        if _check_server_running():
            return True

    typer.echo("❌ 服务启动失败", err=True)
    return False


def _execute(command: str, args: dict) -> dict:
    """通过 RPC 执行命令"""
    if not _ensure_server_running():
        return {"success": False, "error": {"message": "服务不可用"}}

    client = _get_client()
    return client.execute(command, args)


@app.command()
def query(
    symbol: str,
    items: Optional[str] = None,
    years: int = 10,
    end_year: Optional[int] = None,
):
    """查询股票财务数据

    Args:
        symbol: 股票代码 (如 600519, 00700)
        items: 数据项列表 (逗号分隔，可包含字段和计算器)
        years: 查询年份数 (默认 10)
        end_year: 结束年份 (默认自动判断)
        
    Examples:
        acorn vi query 600519 --items revenue,net_profit,roe
        acorn vi query 600519 --items implied_growth
        acorn vi query 00700 --items revenue,operating_cash_flow --years 5
    """
    response = _execute("vi_query", {
        "symbol": symbol,
        "items": items,
        "years": years,
        "end_year": end_year,
    })

    if response.get("success"):
        typer.echo(f"✓ Query successful: {response.get('data')}")
    else:
        error = response.get("error", {})
        typer.echo(f"✗ Error: {error.get('message', error)}")


@app.command()
def list(
    category: Optional[str] = None,
    source: Optional[str] = None,
):
    """列出可用的数据项 (统一 items 概念)
    
    Args:
        category: 按分类筛选 (field/calculator)
        source: 按来源筛选
        
    Examples:
        acorn vi list
        acorn vi list --category calculator
        acorn vi list --source ifrs
    """
    # 列出字段
    if category is None or category == "field":
        response = _execute("vi_list_fields", {
            "source": source,
        })
        if response.get("success"):
            data = response.get("data") or {}
            fields_by_source = data.get("by_source", {}) if isinstance(data, dict) else {}
            if fields_by_source:
                typer.echo("\n📊 Fields:")
                for src, fields in fields_by_source.items():
                    typer.echo(f"  [{src}]")
                    for field in fields[:10]:
                        typer.echo(f"    • {field}")
                    if len(fields) > 10:
                        typer.echo(f"    ... and {len(fields) - 10} more")
    
    # 列出计算器
    if category is None or category == "calculator":
        response = _execute("vi_list_calculators", {})
        if response.get("success"):
            data = response.get("data") or {}
            calcs = data.get("calculators", []) if isinstance(data, dict) else data
            if calcs:
                typer.echo("\n🧮 Calculators:")
                for calc in calcs:
                    if isinstance(calc, dict):
                        name = calc.get("name", str(calc))
                        desc = calc.get("description", "")
                        deps = calc.get("required_fields", [])
                        deps_str = f" (requires: {', '.join(deps)})" if deps else ""
                        typer.echo(f"  • {name}{deps_str}")
                        if desc:
                            typer.echo(f"    {desc}")


@app.command("list-calculators")
def list_calculators():
    """列出可用计算器"""
    response = _execute("vi_list_calculators", {})

    if response.get("success"):
        data = response.get("data") or {}
        calcs = data.get("calculators", []) if isinstance(data, dict) else data
        if calcs:
            for calc in calcs:
                if isinstance(calc, dict):
                    name = calc.get("name", str(calc))
                    desc = calc.get("description", "")
                    if desc:
                        typer.echo(f"  • {name}: {desc}")
                    else:
                        typer.echo(f"  • {name}")
                else:
                    typer.echo(f"  • {calc}")
        else:
            typer.echo("No calculators found")
    else:
        error = response.get("error", {})
        typer.echo(f"✗ Error: {error.get('message', error)}")
