"""
Acorn CLI
=========
插件管理命令行工具，使用 typer 实现。

架构：
- 后台服务模式：插件只加载一次，命令通过 RPC 调用
- 首次运行自动启动服务
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Optional

import typer

from .registry import PluginRegistry
from .tui import run_config_tui

# 默认 socket 路径
DEFAULT_SOCKET_PATH = Path.home() / ".acorn" / "agent.sock"

# config 子命令应用
config_app = typer.Typer(help="配置插件")

# 主应用
app = typer.Typer(
    name="acorn",
    help="🌰 Acorn - 插件化命令行工具\n\n"
         "插件命令:\n"
         "  vi                          Value Investment",
    epilog="运行 'acorn <command> --help' 查看详细帮助",
)

# 将 config_app 注册为子命令
app.add_typer(config_app, name="config")


def get_registry() -> PluginRegistry:
    """获取注册表实例"""
    return PluginRegistry()


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
    
    # 获取 acorn-agent 脚本路径
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
    
    # 等待服务启动
    import time
    for _ in range(10):
        time.sleep(0.3)
        if _check_server_running():
            return True
    
    typer.echo("❌ 服务启动失败", err=True)
    return False


def _execute_via_rpc(command: str, args: dict) -> dict:
    """通过 RPC 执行命令"""
    if not _ensure_server_running():
        return {"success": False, "error": {"message": "服务不可用"}}
    
    client = _get_client()
    return client.execute(command, args)


@app.command()
def install(
    source: str,
    name: Optional[str] = None,
    entry_point: Optional[str] = None,
) -> None:
    """安装插件

    Args:
        source: 插件来源 (包名/路径/Git URL)
        name: 插件名称 (可选)
        entry_point: 入口点 (可选)
    """
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
    """卸载插件

    Args:
        name: 插件名称
        yes: 跳过确认
    """
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


# 动态加载插件命令到主 app
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
