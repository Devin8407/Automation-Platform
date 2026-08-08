"""Tests for workflow execution HTTP schemas."""

from datetime import UTC, datetime
from uuid import uuid4

from automation_platform.domain import (
    TaskOutput,
    TaskStatus,
    WorkflowExecution,
    WorkflowStatus,
)
from automation_platform.runtime.api.schemas import GetWorkflowExecutionResponse


def test_task_execution_response_maps_domain_values(
    task_execution_factory,
):
    """A task execution should map all API-visible domain fields."""

    started_at = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    completed_at = datetime(2026, 1, 1, 12, 1, tzinfo=UTC)

    task = task_execution_factory(
        key="fetch",
        plugin_type="http",
        status=TaskStatus.COMPLETED,
        output=TaskOutput({"result": 42}),
        error_message=None,
        started_at=started_at,
        completed_at=completed_at,
    )

    workflow_execution = WorkflowExecution(
        id=uuid4(),
        workflow_definition_id=uuid4(),
        status=WorkflowStatus.COMPLETED,
        task_executions=[task],
        created_at=datetime(2026, 1, 1, 11, 0, tzinfo=UTC),
        started_at=started_at,
        completed_at=completed_at,
    )

    response = GetWorkflowExecutionResponse.from_domain(workflow_execution)
    result = response.task_executions[0]

    assert result.id == task.id
    assert result.task_definition_id == task.task_definition_id
    assert result.key == "fetch"
    assert result.plugin_type == "http"
    assert result.status == "COMPLETED"
    assert result.output == {"result": 42}
    assert result.error_message is None
    assert result.started_at == started_at
    assert result.completed_at == completed_at


def test_task_execution_response_maps_missing_output(
    task_execution_factory,
):
    """A task without output should expose null output."""

    task = task_execution_factory(output=None)

    workflow_execution = WorkflowExecution(
        id=uuid4(),
        workflow_definition_id=uuid4(),
        status=WorkflowStatus.RUNNING,
        task_executions=[task],
        created_at=datetime(2026, 1, 1, 11, 0, tzinfo=UTC),
        started_at=None,
        completed_at=None,
    )

    response = GetWorkflowExecutionResponse.from_domain(workflow_execution)

    assert response.task_executions[0].output is None


def test_workflow_execution_response_maps_domain_values(
    workflow_execution_factory,
    task_execution_factory,
):
    """A workflow execution should map its state and task executions."""

    created_at = datetime(2026, 1, 1, 11, 0, tzinfo=UTC)
    started_at = datetime(2026, 1, 1, 11, 1, tzinfo=UTC)

    first_task = task_execution_factory(
        key="first",
        status=TaskStatus.COMPLETED,
        output=TaskOutput({"value": 1}),
    )
    second_task = task_execution_factory(
        key="second",
        status=TaskStatus.PENDING,
        output=None,
        error_message="Waiting.",
    )

    workflow_execution = workflow_execution_factory(
        status=WorkflowStatus.RUNNING,
        task_executions=[first_task, second_task],
        created_at=created_at,
        started_at=started_at,
        completed_at=None,
    )

    response = GetWorkflowExecutionResponse.from_domain(workflow_execution)

    assert response.id == workflow_execution.id
    assert response.workflow_definition_id == workflow_execution.workflow_definition_id
    assert response.status == "RUNNING"
    assert response.created_at == created_at
    assert response.started_at == started_at
    assert response.completed_at is None

    assert [task.key for task in response.task_executions] == [
        "first",
        "second",
    ]
    assert response.task_executions[0].output == {"value": 1}
    assert response.task_executions[1].error_message == "Waiting."
