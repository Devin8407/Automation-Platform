"""Base interface for workflow task plugins."""

from __future__ import annotations

from abc import abstractmethod

from ...domain import TaskContext, TaskOutput
from .._plugin import Plugin


class Task(Plugin):
    """
    Base interface for workflow task plugins.
    """

    @abstractmethod
    def execute(self, context: TaskContext) -> TaskOutput:
        """
        Execute the task.

        Parameters:
            configuration: Task-specific configuration supplied by the workflow definition.
        """
        ...
