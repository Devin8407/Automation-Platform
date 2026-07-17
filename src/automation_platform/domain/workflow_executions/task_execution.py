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


@dataclass(slots=True)
class TaskExecution:
    """Runtime state for an executing task."""

    id: UUID

    workflow_execution_id: UUID

    task_definition_id: UUID

    status: TaskStatus = TaskStatus.PENDING

    remaining_dependencies: int = 0

    child_task_ids: list[UUID] = field(default_factory=list)

    retry_count: int = 0

    result: Any | None = None

    error_message: str | None = None

    started_at: datetime | None = None

    completed_at: datetime | None = None

    def is_runnable(self) -> bool:
        """Return whether this task is ready to execute."""

        return self.status == TaskStatus.PENDING and self.remaining_dependencies == 0

    def can_retry(self, max_retries: int) -> bool:
        """Return whether another retry is permitted."""

        return self.retry_count < max_retries

    def is_finished(self) -> bool:
        """Return whether the task has reached a terminal state."""

        return self.status in {
            TaskStatus.COMPLETED,
            TaskStatus.FAILED,
            TaskStatus.CANCELLED,
        }
