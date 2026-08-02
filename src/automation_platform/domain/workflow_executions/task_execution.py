"""
Task execution domain model.

Task executions represent the runtime state of a single task within
a workflow execution.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID

from ..common.enums import TaskStatus
from ..execution_runtime import TaskOutput


@dataclass(slots=True)
class TaskExecution:
    """Runtime state for an executing task."""

    id: UUID

    workflow_execution_id: UUID
    task_definition_id: UUID

    key: str
    plugin_type: str
    configuration: dict[str, Any] = field(default_factory=dict)

    status: TaskStatus = TaskStatus.PENDING
    remaining_dependencies: int = 0
    remaining_tries: int = 0

    parent_task_ids: list[UUID] = field(default_factory=list)
    child_task_ids: list[UUID] = field(default_factory=list)

    output: TaskOutput | None = None

    error_message: str | None = None

    started_at: datetime | None = None
    completed_at: datetime | None = None
