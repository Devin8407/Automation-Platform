"""
workflow execution persistence results models.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from ...domain import TaskOutput


@dataclass(frozen=True)
class CompleteTaskExecutionRequest:
    """Necessary inputs to complete a task"""

    task_execution_id: UUID
    output: TaskOutput
    completed_at: datetime


@dataclass(frozen=True)
class RetryTaskExecutionRequest:
    """Necessary inputs to complete a task"""

    task_execution_id: UUID
    error_message: str | None
    completed_at: datetime


@dataclass(frozen=True)
class StartTaskExecutionResult:
    """Execution data required to process a task."""

    plugin_type: str
    configuration: dict[str, Any]
    parent_outputs: dict[str, TaskOutput]


@dataclass(frozen=True)
class CompleteTaskExecutionResult:
    """Results from completing a task execution in persistence."""

    runnable_task_execution_ids: list[UUID]
    workflow_completed: bool


@dataclass(frozen=True)
class RetryTaskExecutionResult:
    """Results from retrying a task execution in persistence."""

    should_retry: bool
    workflow_failed: bool


@dataclass(frozen=True)
class CompleteTaskExecutionHelperResult:
    """Results from task completion helper."""

    succeeded: bool
    child_task_ids: list[UUID]
    workflow_execution_id: UUID | None


@dataclass(frozen=True)
class RetryTaskExecutionHelperResult:
    """Results from task retry helper."""

    succeeded: bool
    should_retry: bool
    workflow_execution_id: UUID | None
