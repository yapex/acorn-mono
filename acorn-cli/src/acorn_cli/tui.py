"""
插件配置 TUI (Terminal User Interface)
======================================
基于 questionary 的交互式插件管理界面。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .registry import PluginRegistry, PluginEntry

try:
    import questionary
    from questionary import Style
    HAS_QUESTIONARY = True
except ImportError:
    HAS_QUESTIONARY = False


# 自定义样式 (仅在 questionary 可用时)
if HAS_QUESTIONARY:
    CUSTOM_STYLE = Style([
        ('qmark', 'fg:cyan bold'),
        ('question', 'fg:white bold'),
        ('answer', 'fg:green bold'),
        ('pointer', 'fg:cyan bold'),
        ('highlighted', 'fg:cyan bold'),
        ('selected', 'fg:green'),
        ('separator', 'fg:gray'),
        ('instruction', 'fg:gray'),
        ('text', 'fg:white'),
    ])
else:
    CUSTOM_STYLE = None


def format_plugin_entry(entry: PluginEntry, max_name: int = 20) -> str:
    """格式化插件条目显示"""
    status = "✓" if entry.enabled else "✗"
    source_icon = {
        "pypi": "📦",
        "local": "📁",
        "git": "🔗",
    }.get(entry.source, "?")

    name = entry.name[:max_name].ljust(max_name)
    version = f"v{entry.version}" if entry.version != "unknown" else ""

    return f"{status} {name} {source_icon} {version}".strip()


def run_config_tui(registry: PluginRegistry) -> bool:
    """
    运行插件配置 TUI

    Args:
        registry: 插件注册表实例

    Returns:
        是否有变更
    """
    if not HAS_QUESTIONARY:
        print("⚠️  需要安装 questionary: uv pip install questionary")
        print("\n当前插件列表:")
        for entry in registry.list():
            status = "✓" if entry.enabled else "✗"
            print(f"  {status} {entry.name}")
        return False

    plugins = registry.list()

    if not plugins:
        print("📭 暂无已安装的插件")
        print("\n安装插件: acorn install <package>")
        return False

    # 构建 choices
    choices = []
    enabled_names = set()

    for entry in plugins:
        label = format_plugin_entry(entry)
        choices.append(questionary.Choice(
            title=label,
            value=entry.name,
            checked=entry.enabled
        ))
        if entry.enabled:
            enabled_names.add(entry.name)

    # 显示选择界面
    print("\n" + "═" * 50)
    print("🌰 Acorn 插件配置")
    print("═" * 50)
    print("使用 ↑↓ 选择，空格 切换，Enter 确认\n")

    selected = questionary.checkbox(
        "选择要启用的插件:",
        choices=choices,
        style=CUSTOM_STYLE,
    ).ask()

    if selected is None:
        # 用户取消
        return False

    # 计算变更
    new_enabled = set(selected)
    statuses = {name: (name in new_enabled) for name in [e.name for e in plugins]}

    # 更新状态
    changed = registry.update_status(statuses)

    if changed > 0:
        print(f"\n✅ 已更新 {changed} 个插件状态")

        # 显示变更摘要
        print("\n当前启用的插件:")
        for entry in registry.get_enabled():
            print(f"  ✓ {entry.name}")
    else:
        print("\n无变更")

    return changed > 0


def run_main_menu(registry: PluginRegistry) -> None:
    """
    运行主菜单

    提供完整的插件管理功能
    """
    if not HAS_QUESTIONARY:
        print("⚠️  需要安装 questionary: uv pip install questionary")
        return

    while True:
        print("\n" + "═" * 50)
        print("🌰 Acorn 插件管理")
        print("═" * 50)

        action = questionary.select(
            "选择操作:",
            choices=[
                questionary.Choice("📋 配置插件 (启用/禁用)", value="config"),
                questionary.Choice("📥 安装插件", value="install"),
                questionary.Choice("📤 卸载插件", value="uninstall"),
                questionary.Choice("📋 查看插件列表", value="list"),
                questionary.Choice("🔍 发现可用插件", value="discover"),
                questionary.Choice("🚪 退出", value="exit"),
            ],
            style=CUSTOM_STYLE,
        ).ask()

        if action is None or action == "exit":
            print("再见! 👋")
            break

        elif action == "config":
            run_config_tui(registry)

        elif action == "install":
            source = questionary.text(
                "输入插件来源 (包名/路径/Git URL):",
                style=CUSTOM_STYLE,
            ).ask()

            if source:
                success, message = registry.install(source)
                print(f"\n{'✅' if success else '❌'} {message}")

        elif action == "uninstall":
            plugins = registry.list()
            if not plugins:
                print("📭 暂无可卸载的插件")
                continue

            choices = [
                questionary.Choice(
                    f"{e.name} ({e.source})",
                    value=e.name
                )
                for e in plugins
            ]

            name = questionary.select(
                "选择要卸载的插件:",
                choices=choices,
                style=CUSTOM_STYLE,
            ).ask()

            if name:
                confirm = questionary.confirm(
                    f"确定要卸载 '{name}' 吗?",
                    default=False,
                    style=CUSTOM_STYLE,
                ).ask()

                if confirm:
                    success, message = registry.uninstall(name)
                    print(f"\n{'✅' if success else '❌'} {message}")

        elif action == "list":
            plugins = registry.list()
            if not plugins:
                print("📭 暂无已安装的插件")
            else:
                print("\n已安装的插件:")
                print("─" * 50)
                for entry in plugins:
                    status = "✓" if entry.enabled else "✗"
                    source = {
                        "pypi": "📦 PyPI",
                        "local": "📁 本地",
                        "git": "🔗 Git",
                    }.get(entry.source, entry.source)
                    print(f"  {status} {entry.name:<20} {source:<10} v{entry.version}")

        elif action == "discover":
            available = registry.discover_available()
            if not available:
                print("✅ 所有可用插件都已注册")
            else:
                print("\n发现未注册的插件:")
                print("─" * 50)
                for p in available:
                    print(f"  • {p['name']:<20} {p['entry_point']}")

                if questionary.confirm(
                    "\n是否注册这些插件?",
                    default=False,
                    style=CUSTOM_STYLE,
                ).ask():
                    for p in available:
                        registry.install(
                            source=p['name'],
                            name=p['name'],
                            entry_point=p['entry_point'],
                        )
                    print(f"✅ 已注册 {len(available)} 个插件")
