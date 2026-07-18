"""Base interface for workflow trigger plugins."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping
from typing import Any, ClassVar


class Trigger(ABC):
    """
    Base interface for workflow trigger plugins.
    """

    plugin_type: ClassVar[str]

    @abstractmethod
    def is_ready(self, configuration: Mapping[str, Any]) -> bool:
        """
        Determine whether a workflow should begin execution.

        Parameters:
            configuration: Trigger-specific configuration supplied by the workflow definition.

        Returns:
            True if the workflow should begin execution.
        """
        ...
