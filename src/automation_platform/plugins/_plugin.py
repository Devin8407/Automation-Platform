"""Base plugin class"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, ClassVar


class Plugin(ABC):
    """Base plugin class"""

    plugin_type: ClassVar[str]

    @classmethod
    @abstractmethod
    def validate_configuration(
        cls,
        configuration: dict[str, Any],
    ) -> None:
        """Validate plugin configuration.

        Args:
            configuration: Plugin-specific configuration to validate.

        Raises:
            InvalidPluginConfigurationError: If the configuration is invalid.
        """

        ...
