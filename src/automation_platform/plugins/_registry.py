"""Registry of plugin implementations keyed by plugin type."""

from __future__ import annotations

from abc import ABC
from typing import ClassVar, Generic, TypeVar

from ._discovery import discover_plugins

T = TypeVar("T")


class PluginRegistry(Generic[T], ABC):
    """Resolves plugin implementations by plugin type."""

    PLUGIN_INTERFACE: ClassVar[type[T]]

    # ==============================================================================================
    # Constructor
    # ==============================================================================================

    def __init__(self) -> None:
        self._implementations: dict[str, type[T]] = {}

        for implementation in discover_plugins(self.PLUGIN_INTERFACE):
            self._register(implementation)

    # ==============================================================================================
    # Public API
    # ==============================================================================================

    def get(self, plugin_type: str) -> type[T]:
        """
        Return the registered implementation class.

        Raises:
            KeyError: If the plugin type is unknown.
        """

        if plugin_type not in self._implementations:
            raise KeyError(f"Unknown plugin type '{plugin_type}'.")

        return self._implementations[plugin_type]

    def contains(self, plugin_type: str) -> bool:
        """Return True if the plugin type exists."""

        return plugin_type in self._implementations

    def supported_types(self) -> set[str]:
        """Return all registered plugin types."""

        return set(self._implementations)

    # ==============================================================================================
    # Private Helpers
    # ==============================================================================================

    def _register(self, implementation: type[T]) -> None:
        """Validate and register a plugin implementation."""

        plugin_type = implementation.plugin_type

        if not plugin_type.strip():
            raise ValueError(f"{implementation.__name__} has an empty plugin_type.")

        if plugin_type in self._implementations:
            existing = self._implementations[plugin_type]

            raise ValueError(
                f"Duplicate plugin type '{plugin_type}' "
                f"defined by {existing.__name__} and {implementation.__name__}."
            )

        self._implementations[plugin_type] = implementation
