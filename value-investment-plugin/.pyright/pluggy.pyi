"""Stub for pluggy package"""
from typing import Any, Callable, TypeVar, overload

F = TypeVar("F", bound=Callable[..., Any])

class HookspecMarker:
    def __init__(self, project_name: str) -> None: ...
    @overload
    def __call__(self, func: F) -> F: ...
    @overload
    def __call__(
        self,
        *,
        firstresult: bool = False,
        historic: bool = False,
        warn_on_impl: Any = None,
    ) -> Callable[[F], F]: ...
    def __call__(
        self,
        func: F | None = None,
        /,
        *,
        firstresult: bool = False,
        historic: bool = False,
        warn_on_impl: Any = None,
    ) -> F | Callable[[F], F]: ...

class HookimplMarker:
    def __init__(self, project_name: str) -> None: ...
    @overload
    def __call__(self, func: F) -> F: ...
    @overload
    def __call__(
        self,
        *,
        hookwrapper: bool = False,
        optionalhook: bool = False,
        tryfirst: bool = False,
        trylast: bool = False,
    ) -> Callable[[F], F]: ...
    def __call__(
        self,
        func: F | None = None,
        /,
        *,
        hookwrapper: bool = False,
        optionalhook: bool = False,
        tryfirst: bool = False,
        trylast: bool = False,
    ) -> F | Callable[[F], F]: ...

class PluginManager:
    def __init__(self, project_name: str) -> None: ...
    def add_hookspecs(self, spec_class: Any) -> None: ...
    def register(self, plugin: Any, name: str | None = None) -> Any: ...
    def unregister(self, plugin: Any) -> None: ...
    def get_plugins(self) -> list[Any]: ...
    def get_name(self, plugin: Any) -> str | None: ...
    def list_name_plugin(self) -> list[tuple[str, Any]]: ...
    def load_setuptools_entrypoints(self, group: str) -> None: ...
    @property
    def hook(self) -> HookNamespace: ...

class HookNamespace:
    def __getattr__(self, name: str) -> HookCaller: ...

class HookCaller:
    def __call__(self, **kwargs: Any) -> list[Any]: ...
