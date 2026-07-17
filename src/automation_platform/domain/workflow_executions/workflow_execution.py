"""
Workflow execution domain model.

Workflow executions represent a single runtime instance of a workflow
definition. Each execution owns the runtime state of all task
executions associated with that workflow.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID

from ..common.enums import WorkflowStatus
from .task_execution import TaskExecution


@dataclass(slots=True)
class WorkflowExecution:
    """Runtime state for a workflow execution."""

    id: UUID

    workflow_definition_id: UUID

    status: WorkflowStatus = WorkflowStatus.PENDING

    task_executions: list[TaskExecution] = field(default_factory=list)

    created_at: datetime = field(default_factory=datetime.now(UTC))
    started_at: datetime | None = None
    completed_at: datetime | None = None

    remaining_tasks: int = 0

    def is_finished(self) -> bool:
        """Return whether this execution has reached a terminal state."""

        return self.status in {
            WorkflowStatus.COMPLETED,
            WorkflowStatus.FAILED,
            WorkflowStatus.CANCELLED,
        }

    def has_remaining_tasks(self) -> bool:
        """Return whether unfinished tasks remain."""

        return self.remaining_tasks > 0
