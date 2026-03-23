"""
Acorn CLI
=========
插件管理命令行工具，使用 typer 实现。

命令:
    acorn install <source>   安装插件
    acorn list               列出已安装插件
    acorn config             配置插件 (子命令: enable/disable/toggle/discover/path)
"""

from __future__ import annotations

from typing import Optional

import typer

from .registry import PluginRegistry
from .tui import run_config_tui

app = typer.Typer(name="acorn", help="🌰 Acorn - 插件化命令行工具")
config_app = typer.Typer(help="配置插件")
app.add_typer(config_app, name="config")

# 全局注册表路径（可通过环境变量覆盖）
_registry_path: Optional[str] = None


def get_registry() -> PluginRegistry:
    """获取注册表实例"""
    return PluginRegistry(path=_registry_path)


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
def enable(name: str) -> None:
    """启用插件

    Args:
        name: 插件名称
    """
    registry = get_registry()
    success, message = registry.enable(name)
    typer.echo(f"{'✅' if success else '❌'} {message}")


@config_app.command()
def disable(name: str) -> None:
    """禁用插件

    Args:
        name: 插件名称
    """
    registry = get_registry()
    success, message = registry.disable(name)
    typer.echo(f"{'✅' if success else '❌'} {message}")


@config_app.command()
def toggle(name: str) -> None:
    """切换插件状态

    Args:
        name: 插件名称
    """
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


@config_app.command()
def tui() -> None:
    """打开交互式配置界面"""
    registry = get_registry()
    run_config_tui(registry)


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
