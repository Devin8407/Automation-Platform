"""Base interface for workflow task plugins."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import ClassVar

from ...domain import TaskContext, TaskOutput


class Task(ABC):
    """
    Base interface for workflow task plugins.
    """

    plugin_type: ClassVar[str]

    @abstractmethod
    def execute(self, context: TaskContext) -> TaskOutput:
        """
        Execute the task.

        Parameters:
            configuration: Task-specific configuration supplied by the workflow definition.
        """
        ...
