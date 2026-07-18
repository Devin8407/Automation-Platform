"""Find all interface implementations"""

from __future__ import annotations

import inspect
from collections.abc import Iterator
from importlib import import_module
from pkgutil import iter_modules
from types import ModuleType
from typing import TypeVar

T = TypeVar("T")


# ==================================================================================================
# Public API
# ==================================================================================================


def discover_plugins(interface: type[T]) -> Iterator[type[T]]:
    """Yield every implementation of the given plugin interface."""

    for module in _import_implementation_modules(interface):
        yield from _find_plugin_implementations(module, interface)


# ==================================================================================================
# Private Helpers
# ==================================================================================================


def _import_implementation_modules(interface: type[T]) -> Iterator[ModuleType]:
    """Import and yield every module in the interface's implementations package."""

    plugin_package = interface.__module__.rsplit(".", 1)[0]

    implementations_package = import_module(f"{plugin_package}.implementations")

    for module_info in iter_modules(implementations_package.__path__):
        yield import_module(f"{implementations_package.__name__}.{module_info.name}")


def _find_plugin_implementations(module: ModuleType, interface: type[T]) -> Iterator[type[T]]:
    """Yield every class in the module that implements the interface."""

    for _, candidate in inspect.getmembers(module, inspect.isclass):
        if candidate is interface:
            continue

        if issubclass(candidate, interface):
            yield candidate
