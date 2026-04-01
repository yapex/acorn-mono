"""
Acorn CLI
=========
插件管理命令行工具，使用 typer 实现。
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Optional

import typer

from .client import AcornClient
from .registry import PluginRegistry
from .tui import run_config_tui

# config 子命令应用
config_app = typer.Typer(help="配置插件")

# vi 子命令应用
vi_app = typer.Typer(help="Value Investment - 财务数据查询")

# 主应用
app = typer.Typer(
    name="acorn",
    help="🌰 Acorn - 插件化命令行工具\n\n"
         "插件命令:\n"
         "  vi                          Value Investment",
    epilog="运行 'acorn <command> --help' 查看详细帮助",
)

# 注册子命令
app.add_typer(config_app, name="config")
app.add_typer(vi_app, name="vi")


def get_registry() -> PluginRegistry:
    """获取注册表实例"""
    return PluginRegistry()


def _get_client() -> AcornClient:
    """获取 RPC 客户端"""
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

    # 等待服务启动
    import time
    for _ in range(20):
        time.sleep(0.5)
        if _check_server_running():
            typer.echo("服务已启动", err=True)
            return True

    typer.echo("❌ 服务启动失败", err=True)
    return False


def _execute_via_rpc(command: str, args: dict) -> dict:
    """通过 HTTP 执行命令"""
    if not _ensure_server_running():
        return {"success": False, "error": {"message": "服务不可用"}}

    try:
        client = _get_client()
        
        # 对于特定命令，直接调用对应的端点
        if command == "status":
            return client.status()
        
        return client.execute(command, args)
    except Exception as e:
        return {"success": False, "error": {"message": str(e)}}


# =============================================================================
# CLI 命令
# =============================================================================

@app.command()
def install(
    source: str,
    name: Optional[str] = None,
    entry_point: Optional[str] = None,
) -> None:
    """安装插件"""
    registry = get_registry()
    success, message = registry.install(
        source=source,
        name=name,
        entry_point=entry_point,
    )
    typer.echo(f"{'✅' if success else '❌'} {message}")


@app.command()
def uninstall(
    name: str,
    yes: bool = typer.Option(False, "--yes", "-y", help="跳过确认"),
) -> None:
    """卸载插件"""
    registry = get_registry()

    if not yes:
        typer.echo(f"即将卸载插件: {name}")
        response = typer.prompt("确认? [y/N] ").strip().lower()
        if response != "y":
            typer.echo("已取消")
            return

    success, message = registry.uninstall(name)
    typer.echo(f"{'✅' if success else '❌'} {message}")


@app.command("list")
def list_plugins() -> None:
    """列出已安装插件"""
    registry = get_registry()
    plugins = registry.list()

    if not plugins:
        typer.echo("📭 暂无已安装的插件")
        typer.echo("\n安装插件: acorn install <package>")
        return

    typer.echo(f"\n📋 已安装插件 ({len(plugins)})")
    typer.echo("─" * 60)

    for entry in plugins:
        status = "✓" if entry.enabled else "✗"
        source_map = {
            "pypi": "📦 PyPI",
            "local": "📁 本地",
            "git": "🔗 Git",
        }
        source = source_map.get(entry.source, entry.source)
        version = f"v{entry.version}" if entry.version != "unknown" else "-"
        typer.echo(f"{status} {entry.name:<20} {source:<10} {version:<12}")

    typer.echo("─" * 60)


@config_app.command()
def tui() -> None:
    """交互式配置插件 (TUI)"""
    registry = get_registry()
    run_config_tui(registry)


@config_app.command()
def enable(name: str) -> None:
    """启用插件"""
    registry = get_registry()
    success, message = registry.enable(name)
    typer.echo(f"{'✅' if success else '❌'} {message}")


@config_app.command()
def disable(name: str) -> None:
    """禁用插件"""
    registry = get_registry()
    success, message = registry.disable(name)
    typer.echo(f"{'✅' if success else '❌'} {message}")


@config_app.command()
def toggle(name: str) -> None:
    """切换插件状态"""
    registry = get_registry()
    success, message = registry.toggle(name)
    typer.echo(f"{'✅' if success else '❌'} {message}")


@config_app.command()
def discover() -> None:
    """发现可用插件"""
    registry = get_registry()
    available = registry.discover_available()

    if not available:
        typer.echo("✅ 所有可用插件都已注册")
        return

    typer.echo(f"\n🔍 发现 {len(available)} 个未注册插件:")
    typer.echo("─" * 60)

    for p in available:
        typer.echo(f"  • {p['name']:<20} {p['entry_point']}")

    typer.echo("\n注册命令: acorn install <name>")


@config_app.command()
def path() -> None:
    """显示注册表路径"""
    registry = get_registry()
    typer.echo(registry.path_str)


# =============================================================================
# Status 命令
# =============================================================================

@app.command()
def status(
    verbose: bool = typer.Option(False, "-v", "--verbose", help="显示详细信息"),
) -> None:
    """显示系统当前状态"""
    result = _execute_via_rpc("status", {})

    if not result.get("success", False):
        typer.echo(f"❌ {result.get('error', {}).get('message', 'Unknown error')}", err=True)
        raise typer.Exit(1)

    data = result.get("data", {})

    sys_status = data.get("status", "unknown")
    if sys_status == "ok":
        typer.echo("🌰 Acorn 系统状态")
        typer.echo("─" * 60)
    else:
        typer.echo(f"⚠️  系统状态: {sys_status}")
        typer.echo("─" * 60)

    plugins = data.get("plugins", [])
    typer.echo(f"\n📦 已加载插件 ({len(plugins)})")

    all_calculators = []
    all_fields = set()

    for plugin in plugins:
        name = plugin.get("name", "unknown")
        error = plugin.get("error")
        desc = plugin.get("description", "")
        capabilities = plugin.get("capabilities", {})

        status_icon = "✅" if not error else "❌"
        desc_str = f" - {desc}" if desc and verbose else ""
        typer.echo(f"  {status_icon} {name}{desc_str}")

        if verbose and error:
            typer.echo(f"      错误: {error}")

        for calc in capabilities.get("calculators", []):
            if calc.get("name") not in [c.get("name") for c in all_calculators]:
                all_calculators.append(calc)

        for field in capabilities.get("fields", []):
            all_fields.add(field)

    typer.echo(f"\n🧮 可用计算器 ({len(all_calculators)})")
    if all_calculators:
        for calc in all_calculators:
            name = calc.get("name", "unknown")
            desc = calc.get("description", "")
            fields = calc.get("required_fields", [])
            typer.echo(f"  • {name}")
            if verbose:
                if desc:
                    typer.echo(f"    描述: {desc}")
                if fields:
                    typer.echo(f"    必需字段: {', '.join(fields)}")
    else:
        typer.echo("  (无)")

    typer.echo(f"\n📋 可用数据项 ({len(all_fields)})")
    typer.echo("  使用 'acorn vi list' 查看完整列表")

    typer.echo("\n" + "─" * 60)
    typer.echo("💡 提示: 查询示例")
    typer.echo("  acorn vi query 600519 --items net_profit,operating_cash_flow --years 10")
    typer.echo("  acorn vi query 600519 --items implied_growth")


# 动态加载插件命令
def load_plugin_commands() -> None:
    """从 entry_points 加载插件贡献的 CLI 命令"""
    from importlib.metadata import entry_points

    try:
        for ep in entry_points(group="acorn.cli.commands"):
            plugin_app = ep.load()
            app.add_typer(plugin_app, name=ep.name)
    except Exception:
        pass


load_plugin_commands()


def main() -> int:
    """CLI 入口"""
    app()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
