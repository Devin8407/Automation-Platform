"""Tests for the workflow execution query application service."""

from uuid import UUID

import pytest

from automation_platform.application import (
    WorkflowExecutionNotFoundError,
    WorkflowExecutionQueryService,
)

# ==================================================================================================
# Successful Retrieval
# ==================================================================================================


def test_get_returns_workflow_execution(
    mock_uow_factory,
    mock_uow,
    workflow_execution_factory,
):
    """Retrieving an existing workflow execution should return it."""

    workflow_execution = workflow_execution_factory()
    mock_uow.workflow_executions.load.return_value = workflow_execution

    service = WorkflowExecutionQueryService(
        uow_factory=mock_uow_factory,
    )

    result = service.get(workflow_execution.id)

    assert result is workflow_execution

    mock_uow.workflow_executions.load.assert_called_once_with(
        workflow_execution.id,
    )


def test_get_uses_requested_workflow_execution_id(
    mock_uow_factory,
    mock_uow,
    workflow_execution_factory,
):
    """Retrieval should load the requested workflow execution identifier."""

    workflow_execution = workflow_execution_factory()
    workflow_execution_id = workflow_execution.id

    mock_uow.workflow_executions.load.return_value = workflow_execution

    service = WorkflowExecutionQueryService(
        uow_factory=mock_uow_factory,
    )

    service.get(workflow_execution_id)

    mock_uow.workflow_executions.load.assert_called_once_with(
        workflow_execution_id,
    )


# ==================================================================================================
# Missing Workflow Execution
# ==================================================================================================


def test_get_raises_when_workflow_execution_does_not_exist(
    mock_uow_factory,
    mock_uow,
):
    """Retrieving a nonexistent workflow execution should raise an error."""

    workflow_execution_id = UUID("12345678-1234-5678-1234-567812345678")

    mock_uow.workflow_executions.load.return_value = None

    service = WorkflowExecutionQueryService(
        uow_factory=mock_uow_factory,
    )

    with pytest.raises(
        WorkflowExecutionNotFoundError,
        match=str(workflow_execution_id),
    ):
        service.get(workflow_execution_id)

    mock_uow.workflow_executions.load.assert_called_once_with(
        workflow_execution_id,
    )


# ==================================================================================================
# Transaction Boundaries
# ==================================================================================================


def test_get_does_not_commit(
    mock_uow_factory,
    mock_uow,
    workflow_execution_factory,
):
    """Querying a workflow execution should not commit the unit of work."""

    workflow_execution = workflow_execution_factory()
    mock_uow.workflow_executions.load.return_value = workflow_execution

    service = WorkflowExecutionQueryService(
        uow_factory=mock_uow_factory,
    )

    service.get(workflow_execution.id)

    mock_uow.commit.assert_not_called()


def test_get_uses_unit_of_work_as_context_manager(
    mock_uow_factory,
    mock_uow,
    workflow_execution_factory,
):
    """Retrieval should create and enter a unit of work."""

    workflow_execution = workflow_execution_factory()
    mock_uow.workflow_executions.load.return_value = workflow_execution

    service = WorkflowExecutionQueryService(
        uow_factory=mock_uow_factory,
    )

    service.get(workflow_execution.id)

    mock_uow_factory.assert_called_once_with()
    mock_uow.__enter__.assert_called_once_with()
    mock_uow.__exit__.assert_called_once()


def test_get_exits_unit_of_work_when_load_fails(
    mock_uow_factory,
    mock_uow,
):
    """Repository failures should propagate while closing the unit of work."""

    workflow_execution_id = UUID("12345678-1234-5678-1234-567812345678")

    mock_uow.workflow_executions.load.side_effect = RuntimeError("Database unavailable.")

    service = WorkflowExecutionQueryService(
        uow_factory=mock_uow_factory,
    )

    with pytest.raises(RuntimeError, match="Database unavailable"):
        service.get(workflow_execution_id)

    mock_uow.__exit__.assert_called_once()
