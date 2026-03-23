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

# 默认 socket 路径
DEFAULT_SOCKET_PATH = Path.home() / ".acorn" / "agent.sock"


def _get_client():
    """获取 RPC 客户端"""
    from acorn_cli.client import AcornClient
    return AcornClient(socket_path=str(DEFAULT_SOCKET_PATH))


def _check_server_running() -> bool:
    """检查服务是否运行"""
    try:
        client = _get_client()
        result = client.execute("health", {})
        return result.get("success", False)
    except Exception:
        return False


def _start_server_background() -> None:
    """后台启动服务"""
    if DEFAULT_SOCKET_PATH.exists():
        DEFAULT_SOCKET_PATH.unlink()
    
    venv_bin = Path(sys.executable).parent
    acorn_agent_script = venv_bin / "acorn-agent"
    
    subprocess.Popen(
        [str(acorn_agent_script)],
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
    
    for _ in range(10):
        time.sleep(0.3)
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
    response = _execute("vi_query", {
        "symbol": symbol,
        "years": years,
        "fields": fields,
        "calculators": calculators,
    })

    if response.get("success"):
        typer.echo(f"✓ Query successful: {response.get('data')}")
    else:
        error = response.get("error", {})
        typer.echo(f"✗ Error: {error.get('message', error)}")


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
    response = _execute("vi_list_fields", {
        "source": source,
        "prefix": prefix,
    })

    if response.get("success"):
        data = response.get("data") or {}
        fields = data.get("fields", []) if isinstance(data, dict) else data
        if fields:
            for field in fields:
                typer.echo(f"  • {field}")
        else:
            typer.echo("No fields found")
    else:
        error = response.get("error", {})
        typer.echo(f"✗ Error: {error.get('message', error)}")


@app.command("list-calculators")
def list_calculators():
    """列出可用计算器"""
    from acorn_core import Task, Acorn

    acorn = Acorn()
    acorn.load_plugins()

    task = Task(command="vi_list_calculators", args={})
    response = acorn.execute(task)

    if response.success:
        data = response.data or {}
        calcs = data.get("calculators", []) if isinstance(data, dict) else data
        if calcs:
            for calc in calcs:
                # calc 可能是 dict 或 str
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
        typer.echo(f"✗ Error: {response.error.message}")
