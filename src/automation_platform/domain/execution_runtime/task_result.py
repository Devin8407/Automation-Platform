"""
Task results domain model.

Task results represent the runtime results of an executed task plugin.
"""

from __future__ import annotations

from dataclasses import dataclass

from .task_output import TaskOutput


@dataclass(slots=True)
class TaskResult:
    """Runtime results of an executed task plugin."""

    succeeded: bool

    output: TaskOutput

    message: str | None = None
