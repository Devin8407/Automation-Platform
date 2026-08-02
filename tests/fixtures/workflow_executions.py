"""
Pytest fixtures for workflow execution domain objects.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

import pytest

from automation_platform.domain.common.enums import (
    TaskStatus,
    WorkflowStatus,
)
from automation_platform.domain.execution_runtime import TaskOutput
from automation_platform.domain.workflow_definitions import WorkflowDefinition
from automation_platform.domain.workflow_executions import (
    TaskExecution,
    WorkflowExecution,
)
from automation_platform.persistence.workflow_definitions import (
    WorkflowDefinitionRepository,
)


@pytest.fixture
def task_execution_factory() -> Callable[..., TaskExecution]:
    """Create task executions for tests."""

    def factory(
        *,
        id: UUID | None = None,
        workflow_execution_id: UUID | None = None,
        task_definition_id: UUID | None = None,
        key: str = "task",
        plugin_type: str = "test.task",
        configuration: dict[Any] | None = None,
        status: TaskStatus = TaskStatus.PENDING,
        remaining_dependencies: int = 0,
        remaining_tries: int = 0,
        parent_task_ids: list[UUID] | None = None,
        child_task_ids: list[UUID] | None = None,
        output: TaskOutput | None = None,
        error_message: str | None = None,
        started_at: datetime | None = None,
        completed_at: datetime | None = None,
    ) -> TaskExecution:
        return TaskExecution(
            id=id or uuid4(),
            workflow_execution_id=workflow_execution_id or uuid4(),
            task_definition_id=task_definition_id or uuid4(),
            key=key,
            plugin_type=plugin_type,
            configuration=configuration or {},
            status=status,
            remaining_dependencies=remaining_dependencies,
            remaining_tries=remaining_tries,
            parent_task_ids=parent_task_ids or [],
            child_task_ids=child_task_ids or [],
            output=output,
            error_message=error_message,
            started_at=started_at,
            completed_at=completed_at,
        )

    return factory


@pytest.fixture
def workflow_execution_factory(
    task_execution_factory: Callable[..., TaskExecution],
) -> Callable[..., WorkflowExecution]:
    """Create workflow executions for tests."""

    def factory(
        *,
        id: UUID | None = None,
        workflow_definition: WorkflowDefinition | None = None,
        workflow_definition_id: UUID | None = None,
        status: WorkflowStatus = WorkflowStatus.RUNNING,
        task_executions: list[TaskExecution] | None = None,
        created_at: datetime | None = None,
        started_at: datetime | None = None,
        completed_at: datetime | None = None,
    ) -> WorkflowExecution:

        execution_id = id or uuid4()

        # Build default task executions from the workflow definition.
        if task_executions is None:
            if workflow_definition is not None:
                task_executions = [
                    task_execution_factory(
                        workflow_execution_id=execution_id,
                        task_definition_id=task.id,
                    )
                    for task in workflow_definition.task_definitions
                ]
            else:
                # Generic domain tests (non-persistence).
                task_executions = [
                    task_execution_factory(
                        workflow_execution_id=execution_id,
                    )
                ]

        return WorkflowExecution(
            id=execution_id,
            workflow_definition_id=(
                workflow_definition.id
                if workflow_definition is not None
                else workflow_definition_id or uuid4()
            ),
            status=status,
            task_executions=task_executions,
            created_at=created_at or datetime.now(UTC),
            started_at=started_at,
            completed_at=completed_at,
        )

    return factory


@pytest.fixture
def persisted_workflow_definition(
    session,
    workflow_definition_factory,
) -> WorkflowDefinition:
    """
    Create and persist a workflow definition.
    """

    definition = workflow_definition_factory()

    WorkflowDefinitionRepository(session).save(definition)
    session.commit()

    return definition
