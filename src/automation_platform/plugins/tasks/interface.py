"""Base interface for workflow task plugins."""

from __future__ import annotations

from abc import abstractmethod

from ...domain import TaskContext, TaskResult
from .._plugin import Plugin


class Task(Plugin):
    """
    Base interface for workflow task plugins.
    """

    @abstractmethod
    def execute(self, context: TaskContext) -> TaskResult:
        """
        Execute the task.

        Parameters:
            configuration: Task-specific configuration supplied by the workflow definition.

        Returns:
            Result holding success, task output, and an optional message
        """
        ...
