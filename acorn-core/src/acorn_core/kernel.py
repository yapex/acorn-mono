"""
种子内核 (The Acorn)
====================
自进化系统的核心引擎。
"""

import importlib
import pkgutil
import uuid
from pathlib import Path
from typing import Any

import pluggy

from .events import EventBus
from .specs import Genes
from .types import Response, Task


class Acorn:
    """
    种子内核 - 管理插件生命周期
    """

    def __init__(self):
        self.pm = pluggy.PluginManager("evo")
        self.pm.add_hookspecs(Genes)
        self._plugins: dict = {}  # plugin_id -> 插件实例
        self._event_bus = EventBus()

    def load_plugins(self, plugin_path: str | Path | None = None):
        """加载插件

        加载顺序：
        1. 内部插件 (通过 entry_points)
        2. 外部路径插件 (可选)
        3. 已安装的外部插件 (通过 setuptools entry_points)
        """
        # 1. 加载内部插件（内置 + 入口点）
        self.pm.load_setuptools_entrypoints("yapex.acorn.plugins")

        # 2. 加载外部路径插件
        if plugin_path:
            self._load_from_path(plugin_path)

        # 3. 发送插件加载完成事件
        for plugin in self.pm.get_plugins():
            plugin_name = self.pm.get_name(plugin)
            if plugin_name:
                self._event_bus.publish("acorn.plugin.loaded", sender=self, plugin_name=plugin_name, plugin=plugin)

        self.pm.hook.on_load()

    def _load_from_path(self, plugin_path: str | Path):
        """从指定路径加载插件"""
        path = Path(plugin_path)
        if not path.exists():
            return

        for _, name, _ in pkgutil.iter_modules([str(path)]):
            if name.startswith("_"):
                continue
            try:
                module = importlib.import_module(f"{path.name}.{name}")
                self._register_plugin_module(module)
            except Exception as e:
                print(f"Warning: Failed to load plugin {name}: {e}")

    def _register_plugin_module(self, module):
        """从模块中注册插件"""
        if hasattr(module, "plugin"):
            self.pm.register(module.plugin, name=getattr(module, "__name__", None))
        elif hasattr(module, "Plugin"):
            self.pm.register(module.Plugin())
        else:
            for name, obj in vars(module).items():
                if name.startswith("_"):
                    continue
                if isinstance(obj, type) and (hasattr(obj, "commands") or hasattr(obj, "handle")):
                    self.pm.register(obj(), name=module.__name__)
                    break

    def install_plugin(self, namespace: dict[str, Any]) -> str:
        """
        动态安装插件

        Args:
            namespace: 执行后的命名空间字典，由调用者负责执行代码

        Returns:
            plugin_id: 插件唯一标识符
        """
        # 查找插件实例
        plugin_instance = None

        for name, obj in namespace.items():
            if name.startswith("_"):
                continue
            if hasattr(obj, "handle") or hasattr(obj, "commands"):
                if callable(obj):
                    plugin_instance = obj()
                else:
                    plugin_instance = obj

        if not plugin_instance:
            raise ValueError("No valid plugin found. Must have handle() or commands.")

        plugin_id = str(uuid.uuid4())[:8]
        self.pm.register(plugin_instance, name=f"dynamic.{plugin_id}")
        self._plugins[plugin_id] = plugin_instance

        return plugin_id

    def uninstall_plugin(self, plugin_id: str) -> bool:
        """卸载插件"""
        plugin = self._plugins.get(plugin_id)
        if plugin:
            self.pm.unregister(plugin)
            del self._plugins[plugin_id]
            return True
        return False

    def execute(self, task: Task) -> Response:
        """
        执行单个任务

        Args:
            task: Task 对象

        Returns:
            Response 对象
        """
        # 1. 查找能处理此命令的插件
        handler = self._find_handler(task.command)

        if handler is None:
            return Response.err(
                code="NOT_IMPLEMENTED",
                message=f"No plugin handles command: {task.command}"
            )

        # 2. 执行处理
        try:
            result = handler.handle(task)

            # 处理返回格式
            if isinstance(result, dict):
                if result.get("success"):
                    return Response.ok(
                        data=result.get("data"),
                        meta={"source_plugin": self._get_plugin_name(handler)}
                    )
                else:
                    error = result.get("error", {})
                    if isinstance(error, dict):
                        return Response.err(
                            code=error.get("code", "PLUGIN_ERROR"),
                            message=error.get("message", "Unknown error")
                        )
                    elif isinstance(error, str):
                        # 支持 "CODE: message" 格式
                        if ":" in error:
                            code, message = error.split(":", 1)
                            return Response.err(
                                code=code.strip(),
                                message=message.strip()
                            )
                        return Response.err(
                            code="PLUGIN_ERROR",
                            message=str(error)
                        )
                    return Response.err(
                        code="PLUGIN_ERROR",
                        message="Unknown error"
                    )
            else:
                return Response.ok(data=result)

        except Exception as e:
            return Response.err(
                code="PLUGIN_ERROR",
                message=f"Plugin execution failed: {e}",
                detail=str(e)
            )

    def execute_batch(self, tasks: list[Task]) -> list[Response]:
        """
        批量执行任务

        Args:
            tasks: Task 对象列表

        Returns:
            Response 对象列表
        """
        return [self.execute(task) for task in tasks]

    def _find_handler(self, command: str):
        """查找能处理命令的插件"""
        for plugin in self.pm.get_plugins():
            if hasattr(plugin, "commands"):
                try:
                    # 支持属性和方法两种形式
                    commands_attr = plugin.commands
                    if callable(commands_attr):
                        commands_result = commands_attr()
                    else:
                        commands_result = commands_attr
                    if isinstance(commands_result, (list, tuple)) and command in commands_result:
                        return plugin
                except Exception:
                    pass
        return None

    def _get_plugin_name(self, plugin) -> str:
        """获取插件名称"""
        name = self.pm.get_name(plugin)
        if name is not None:
            return name.split(".")[-1]
        if hasattr(plugin, "name") and isinstance(plugin.name, str):
            return plugin.name
        return type(plugin).__name__

    def list_capabilities(self) -> list[dict]:
        """列出所有插件声明的能力"""
        capabilities = []
        for plugin in self.pm.get_plugins():
            if hasattr(plugin, "get_capabilities"):
                try:
                    caps = plugin.get_capabilities()
                    if caps:
                        if isinstance(caps, list):
                            capabilities.extend(caps)
                        else:
                            capabilities.append(caps)
                except Exception:
                    pass
        return capabilities

    def list_plugins(self) -> list:
        """列出所有已加载的插件"""
        return self.pm.list_name_plugin()

    def shutdown(self):
        """关闭系统"""
        self.pm.hook.on_unload()

    def __enter__(self):
        self.load_plugins()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.shutdown()
        return False
