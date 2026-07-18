"""
Task context domain model.

Task context represent the information necessary to execute a task plugin.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .task_output import TaskOutput


@dataclass(slots=True)
class TaskContext:
    """Runtime context needed to execute a task plugin."""

    configuration: dict[str, Any] = field(default_factory=dict)

    inputs: dict[str, TaskOutput] = field(default_factory=dict)
