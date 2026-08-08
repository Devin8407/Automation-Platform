"""HTTP schemas for workflow executions."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel

from ....domain import TaskExecution, WorkflowExecution


class TaskExecutionResponse(BaseModel):
    """HTTP representation of a task execution."""

    id: UUID
    task_definition_id: UUID
    key: str
    plugin_type: str
    status: str
    output: dict[str, Any] | None
    error_message: str | None
    started_at: datetime | None
    completed_at: datetime | None

    @classmethod
    def from_domain(cls, task_execution: TaskExecution) -> TaskExecutionResponse:
        """Create an HTTP response model from a domain task execution."""

        return cls(
            id=task_execution.id,
            task_definition_id=task_execution.task_definition_id,
            key=task_execution.key,
            plugin_type=task_execution.plugin_type,
            status=task_execution.status.name,
            output=(task_execution.output.values if task_execution.output is not None else None),
            error_message=task_execution.error_message,
            started_at=task_execution.started_at,
            completed_at=task_execution.completed_at,
        )


class GetWorkflowExecutionResponse(BaseModel):
    """HTTP representation of a workflow execution."""

    id: UUID
    workflow_definition_id: UUID
    status: str
    task_executions: list[TaskExecutionResponse]
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None

    @classmethod
    def from_domain(cls, workflow_execution: WorkflowExecution) -> GetWorkflowExecutionResponse:
        """Create an HTTP response model from a domain workflow execution."""

        return cls(
            id=workflow_execution.id,
            workflow_definition_id=workflow_execution.workflow_definition_id,
            status=workflow_execution.status.name,
            task_executions=[
                TaskExecutionResponse.from_domain(task_execution)
                for task_execution in workflow_execution.task_executions
            ],
            created_at=workflow_execution.created_at,
            started_at=workflow_execution.started_at,
            completed_at=workflow_execution.completed_at,
        )
