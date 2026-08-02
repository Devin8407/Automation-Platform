"""
Tests for workflow execution mapping.
"""

from uuid import uuid4

from automation_platform.domain import TaskOutput
from automation_platform.persistence.workflow_executions._mapper import (
    WorkflowExecutionMapper,
)
from automation_platform.persistence.workflow_executions._model import (
    TaskExecutionModel,
    WorkflowExecutionModel,
)


def test_task_round_trip(task_execution_factory) -> None:
    """Task execution survives a mapper round-trip."""

    original = task_execution_factory()

    model = WorkflowExecutionMapper.task_to_model(original)

    reconstructed = WorkflowExecutionMapper.task_to_domain(model)

    assert reconstructed == original


def test_workflow_round_trip(workflow_execution_factory) -> None:
    """Workflow executions survive a mapper round-trip."""

    original = workflow_execution_factory()

    model = WorkflowExecutionMapper.workflow_to_model(original)

    reconstructed = WorkflowExecutionMapper.workflow_to_domain(
        model,
        [
            WorkflowExecutionMapper.task_to_domain(task_model)
            for task_model in model.task_executions
        ],
    )

    assert reconstructed == original


def test_workflow_to_model(workflow_execution_factory) -> None:
    """Workflow executions are mapped to SQLAlchemy models."""

    workflow = workflow_execution_factory()

    model = WorkflowExecutionMapper.workflow_to_model(workflow)

    assert isinstance(model, WorkflowExecutionModel)

    assert model.id == workflow.id
    assert model.workflow_definition_id == workflow.workflow_definition_id
    assert model.status == workflow.status
    assert model.created_at == workflow.created_at
    assert model.started_at == workflow.started_at
    assert model.completed_at == workflow.completed_at


def test_workflow_to_domain(task_execution_factory) -> None:
    """Workflow execution models are mapped to domain objects."""

    model = WorkflowExecutionModel(
        id=uuid4(),
        workflow_definition_id=uuid4(),
        status="PENDING",
        created_at=task_execution_factory().started_at,
        started_at=None,
        completed_at=None,
    )

    task_executions = [
        task_execution_factory(),
        task_execution_factory(),
    ]

    workflow = WorkflowExecutionMapper.workflow_to_domain(
        model,
        task_executions,
    )

    assert workflow.id == model.id
    assert workflow.workflow_definition_id == model.workflow_definition_id
    assert workflow.status == model.status
    assert workflow.task_executions == task_executions
    assert workflow.created_at == model.created_at
    assert workflow.started_at == model.started_at
    assert workflow.completed_at == model.completed_at


def test_task_to_model(task_execution_factory) -> None:
    """Task executions are mapped to SQLAlchemy models."""

    task = task_execution_factory(
        output=TaskOutput({"value": 123}),
    )

    model = WorkflowExecutionMapper.task_to_model(task)

    assert isinstance(model, TaskExecutionModel)

    assert model.id == task.id
    assert model.workflow_execution_id == task.workflow_execution_id
    assert model.task_definition_id == task.task_definition_id
    assert model.key == task.key
    assert model.plugin_type == task.plugin_type
    assert model.configuration == task.configuration
    assert model.status == task.status
    assert model.remaining_dependencies == task.remaining_dependencies
    assert model.parent_task_ids == task.parent_task_ids
    assert model.child_task_ids == task.child_task_ids
    assert model.remaining_tries == task.remaining_tries

    assert model.output == {"value": 123}

    assert model.error_message == task.error_message
    assert model.started_at == task.started_at
    assert model.completed_at == task.completed_at


def test_task_to_model_maps_none_output(task_execution_factory) -> None:
    """Missing task output remains None in persistence."""

    task = task_execution_factory(output=None)

    model = WorkflowExecutionMapper.task_to_model(task)

    assert model.output is None


def test_output_to_domain() -> None:
    """Persisted task output is mapped to a domain TaskOutput."""

    output = WorkflowExecutionMapper.output_to_domain(
        {"value": 123},
    )

    assert output == TaskOutput({"value": 123})


def test_output_to_domain_returns_none_for_none() -> None:
    """Missing persisted task output remains None."""

    assert WorkflowExecutionMapper.output_to_domain(None) is None


def test_task_to_domain(task_execution_factory) -> None:
    """Task execution models are mapped to domain objects."""

    task = task_execution_factory()

    model = TaskExecutionModel(
        id=task.id,
        workflow_execution_id=task.workflow_execution_id,
        task_definition_id=task.task_definition_id,
        key=task.key,
        plugin_type=task.plugin_type,
        configuration=task.configuration,
        status=task.status,
        remaining_dependencies=task.remaining_dependencies,
        parent_task_ids=task.parent_task_ids,
        child_task_ids=task.child_task_ids,
        remaining_tries=task.remaining_tries,
        output=task.output,
        error_message=task.error_message,
        started_at=task.started_at,
        completed_at=task.completed_at,
    )

    domain = WorkflowExecutionMapper.task_to_domain(model)

    assert domain == task
