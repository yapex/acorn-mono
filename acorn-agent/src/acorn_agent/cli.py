"""Acorn Agent CLI - Client and Server

Usage:
    # Start server (default)
    acorn-agent

    # Client commands (auto-starts server if needed)
    acorn-agent query <symbol> [-r <fields>] [-y <years>] [-c <calculators>]
    acorn-agent list-fields [--source <source>] [--prefix <prefix>]
    acorn-agent list-calculators
    acorn-agent call <command> --args '<json>'
"""
from __future__ import annotations

import json
import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Optional

import typer
from typing_extensions import Annotated

from .client import AcornClient
from .formatter import _format_output

# Default socket path
DEFAULT_SOCKET_PATH = Path.home() / ".acorn" / "agent.sock"

# Typer app
app = typer.Typer(help="Acorn Agent CLI - Unix Socket RPC Client")


def _get_client() -> AcornClient:
    """Get RPC client instance"""
    return AcornClient(socket_path=str(DEFAULT_SOCKET_PATH))


def _check_server_running(client: AcornClient) -> bool:
    """Check if server is running"""
    try:
        result = client.execute("health", {})
        return result.get("success", False)
    except Exception:
        return False


def _start_server_background() -> None:
    """Start server in background, detached from current process"""
    # Remove old socket if exists
    if DEFAULT_SOCKET_PATH.exists():
        DEFAULT_SOCKET_PATH.unlink()
    
    # Get the path to the virtual environment scripts directory
    venv_bin = Path(sys.executable).parent
    venv_dir = venv_bin.parent
    acorn_agent_script = venv_bin / "acorn-agent"
    
    # Start server in background using the installed script
    subprocess.Popen(
        [str(acorn_agent_script)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
        cwd=str(venv_dir),
    )


def _ensure_server_running(client: AcornClient) -> bool:
    """Ensure server is running, start if not"""
    if _check_server_running(client):
        return True
    
    typer.echo("Starting acorn-agent server...", err=True)
    _start_server_background()
    
    # Wait for server to be ready
    max_wait = 10  # seconds
    interval = 0.5  # seconds
    
    for i in range(int(max_wait / interval)):
        time.sleep(interval)
        if _check_server_running(client):
            typer.echo("Server started.", err=True)
            return True
    
    typer.echo("Failed to start server.", err=True)
    return False


@app.command("query")
def query(
    symbol: str = typer.Argument(..., help="Stock symbol (e.g. 600519, 000001)"),
    fields: str = typer.Option("all", "-r", "--fields", help="Comma-separated fields"),
    years: int = typer.Option(10, "-y", "--years", help="Number of years"),
    calculators: str = typer.Option("", "-c", "--calculators", help="Comma-separated calculators"),
    wacc: float = typer.Option(0.08, "--wacc", help="WACC for DCF calculations"),
    g_terminal: float = typer.Option(0.03, "--g-terminal", help="Terminal growth rate"),
    format: str = typer.Option("table", "--format", help="Output format: table, json"),
) -> None:
    """Query financial data for a stock"""
    client = _get_client()

    if not _ensure_server_running(client):
        raise typer.Exit(1)

    # Build calculator config
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

    result = client.execute("vi_query", {
        "symbol": symbol,
        "fields": fields,
        "years": years,
        "calculators": calculators,
        "calculator_config": calc_config,
    })

    if not result.get("success", False):
        error = result.get("error", {})
        typer.echo(f"Error: {error.get('message', 'Unknown error')}", err=True)
        raise typer.Exit(1)

    data = result.get("data", {})

    # Output
    if format.lower() == "json":
        typer.echo(_format_output(data, "json"))
    else:
        end_year = data.get("end_year", "N/A")
        start_year = end_year - years + 1 if isinstance(end_year, int) else "N/A"
        typer.echo(f"\n=== {symbol} 查询结果 ===")
        typer.echo(f"字段: {fields}")
        typer.echo(f"年份范围: {start_year} - {end_year}")
        typer.echo()
        typer.echo(_format_output(data, "table"))


@app.command("list-fields")
def list_fields(
    source: Annotated[Optional[str], typer.Option("--source", help="Filter by source")] = None,
    prefix: Annotated[Optional[str], typer.Option("--prefix", help="Filter by prefix")] = None,
) -> None:
    """List all available fields"""
    client = _get_client()

    if not _ensure_server_running(client):
        raise typer.Exit(1)

    result = client.execute("vi_list_fields", {"source": source, "prefix": prefix})

    if not result.get("success", False):
        error = result.get("error", {})
        typer.echo(f"Error: {error.get('message', 'Unknown error')}", err=True)
        raise typer.Exit(1)

    data = result.get("data", {})
    fields = data.get("fields", [])
    by_source = data.get("by_source", {})

    typer.echo(f"\n可用字段 ({len(fields)}):\n")

    if by_source:
        for src, fs in sorted(by_source.items()):
            typer.echo(f"  [{src}]")
            for f in fs:
                typer.echo(f"    - {f}")
            typer.echo()
    else:
        for f in fields:
            typer.echo(f"  - {f}")


@app.command("list-calculators")
def list_calculators() -> None:
    """List all available calculators"""
    client = _get_client()

    if not _ensure_server_running(client):
        raise typer.Exit(1)

    result = client.execute("vi_list_calculators", {})

    if not result.get("success", False):
        error = result.get("error", {})
        typer.echo(f"Error: {error.get('message', 'Unknown error')}", err=True)
        raise typer.Exit(1)

    calcs = result.get("data", {}).get("calculators", [])

    typer.echo(f"\n可用计算器 ({len(calcs)}):\n")

    for calc in calcs:
        typer.echo(f"  {calc.get('name', 'unknown')}")
        typer.echo(f"    描述: {calc.get('description', 'N/A')}")
        typer.echo(f"    必需字段: {', '.join(calc.get('required_fields', []))}")
        typer.echo()


@app.command("call")
def call(
    command: str = typer.Argument(..., help="RPC command name"),
    args: str = typer.Option('{}', "--args", help="JSON arguments string"),
) -> None:
    """Execute a raw RPC command (for debugging)"""
    client = _get_client()

    if not _ensure_server_running(client):
        raise typer.Exit(1)

    try:
        parsed_args = json.loads(args)
    except json.JSONDecodeError as e:
        typer.echo(f"Error: Invalid JSON in --args: {e}", err=True)
        raise typer.Exit(1)

    result = client.execute(command, parsed_args)
    typer.echo(json.dumps(result, indent=2, ensure_ascii=False, default=str))


def _start_server() -> None:
    """Start the agent server (legacy entry point)"""
    from .server import AcornServer

    server = AcornServer()

    def signal_handler(sig, frame):
        typer.echo("\nShutting down...")
        server.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        server.start()
    except KeyboardInterrupt:
        server.stop()


def main() -> None:
    """Main entry point - auto-detect server vs client mode"""
    # If no arguments, start server
    if len(sys.argv) == 1:
        _start_server()
    else:
        app()


if __name__ == "__main__":
    main()
