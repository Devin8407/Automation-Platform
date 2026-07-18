"""
Task results domain model.

Task results represent the runtime results of an executed task plugin.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..common.enums import TaskStatus
from .task_output import TaskOutput


@dataclass(slots=True)
class TaskResult:
    """Runtime results of an executed task plugin."""

    status: TaskStatus

    output: TaskOutput

    message: str | None = None
