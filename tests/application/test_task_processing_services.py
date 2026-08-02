"""Tests for the task processing application service."""

from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from automation_platform.application.task_processing.services import (
    TaskProcessingService,
)
from automation_platform.domain import TaskContext, TaskOutput
from automation_platform.persistence import (
    CompleteTaskExecutionResult,
    RetryTaskExecutionResult,
)

# ==================================================================================================
# Successful Processing
# ==================================================================================================


def test_process_executes_plugin_with_task_context(
    mock_task_processing_service,
    start_task_result_factory,
    successful_task_result_factory,
    mock_uow,
    mock_task_registry,
    mock_task_plugin_type,
    mock_task_plugin,
):
    """Processing should execute the registered plugin with the task context."""

    task = start_task_result_factory(
        plugin_type="test_task",
        configuration={"name": "example"},
    )
    plugin_result = successful_task_result_factory()

    mock_uow.workflow_executions.start_task.return_value = task
    mock_task_plugin.execute.return_value = plugin_result

    mock_uow.workflow_executions.complete_task.return_value = CompleteTaskExecutionResult(
        runnable_task_execution_ids=[],
        workflow_completed=False,
    )

    mock_task_processing_service.process(uuid4())

    mock_task_registry.get.assert_called_once_with("test_task")
    mock_task_plugin_type.assert_called_once_with()

    mock_task_plugin.execute.assert_called_once_with(
        TaskContext(
            configuration={"name": "example"},
            inputs=task.parent_outputs,
        )
    )


def test_process_completes_successful_task(
    mock_task_processing_service,
    start_task_result_factory,
    successful_task_result_factory,
    mock_uow,
    mock_task_plugin,
):
    """Successful plugin execution should complete the task."""

    output = TaskOutput(
        values={
            "result": 42,
        }
    )

    task = start_task_result_factory()
    plugin_result = successful_task_result_factory(output=output)

    mock_uow.workflow_executions.start_task.return_value = task
    mock_task_plugin.execute.return_value = plugin_result

    mock_uow.workflow_executions.complete_task.return_value = CompleteTaskExecutionResult(
        runnable_task_execution_ids=[],
        workflow_completed=False,
    )

    task_execution_id = uuid4()

    mock_task_processing_service.process(task_execution_id)

    mock_uow.workflow_executions.complete_task.assert_called_once()

    request = mock_uow.workflow_executions.complete_task.call_args.args[0]

    assert request.task_execution_id == task_execution_id
    assert request.output == output
    assert request.completed_at is not None
    assert request.completed_at.utcoffset().total_seconds() == 0

    mock_uow.workflow_executions.retry_task.assert_not_called()


def test_process_returns_newly_runnable_tasks(
    mock_task_processing_service,
    start_task_result_factory,
    successful_task_result_factory,
    mock_uow,
    mock_task_plugin,
):
    """Successful processing should return newly runnable child tasks."""

    child_a = uuid4()
    child_b = uuid4()

    mock_uow.workflow_executions.start_task.return_value = start_task_result_factory()
    mock_task_plugin.execute.return_value = successful_task_result_factory()

    mock_uow.workflow_executions.complete_task.return_value = CompleteTaskExecutionResult(
        runnable_task_execution_ids=[
            child_a,
            child_b,
        ],
        workflow_completed=False,
    )

    result = mock_task_processing_service.process(uuid4())

    assert result.enqueue_task_ids == [
        child_a,
        child_b,
    ]
    assert result.should_retry is False


# ==================================================================================================
# Failed Processing
# ==================================================================================================


def test_process_records_failed_task_attempt(
    mock_task_processing_service,
    start_task_result_factory,
    failed_task_result_factory,
    mock_uow,
    mock_task_plugin,
):
    """A plugin-declared failure should record a failed task attempt."""

    mock_uow.workflow_executions.start_task.return_value = start_task_result_factory()
    mock_task_plugin.execute.return_value = failed_task_result_factory(
        message="Something went wrong.",
    )

    mock_uow.workflow_executions.retry_task.return_value = RetryTaskExecutionResult(
        should_retry=True,
        workflow_failed=False,
    )

    task_execution_id = uuid4()

    mock_task_processing_service.process(task_execution_id)

    mock_uow.workflow_executions.retry_task.assert_called_once()

    request = mock_uow.workflow_executions.retry_task.call_args.args[0]

    assert request.task_execution_id == task_execution_id
    assert request.error_message == "Something went wrong."
    assert request.completed_at is not None
    assert request.completed_at.utcoffset().total_seconds() == 0

    mock_uow.workflow_executions.complete_task.assert_not_called()


def test_process_requests_retry_when_tries_remain(
    mock_task_processing_service,
    start_task_result_factory,
    failed_task_result_factory,
    mock_uow,
    mock_task_plugin,
):
    """A retryable task failure should request another processing attempt."""

    mock_uow.workflow_executions.start_task.return_value = start_task_result_factory()
    mock_task_plugin.execute.return_value = failed_task_result_factory()

    mock_uow.workflow_executions.retry_task.return_value = RetryTaskExecutionResult(
        should_retry=True,
        workflow_failed=False,
    )

    result = mock_task_processing_service.process(uuid4())

    assert result.enqueue_task_ids == []
    assert result.should_retry is True


def test_process_does_not_retry_terminal_failure(
    mock_task_processing_service,
    start_task_result_factory,
    failed_task_result_factory,
    mock_uow,
    mock_task_plugin,
):
    """A terminal task failure should not request another processing attempt."""

    mock_uow.workflow_executions.start_task.return_value = start_task_result_factory()
    mock_task_plugin.execute.return_value = failed_task_result_factory()

    mock_uow.workflow_executions.retry_task.return_value = RetryTaskExecutionResult(
        should_retry=False,
        workflow_failed=True,
    )

    result = mock_task_processing_service.process(uuid4())

    assert result.enqueue_task_ids == []
    assert result.should_retry is False


# ==================================================================================================
# Unprocessable Tasks
# ==================================================================================================


def test_process_does_not_execute_unprocessable_task(
    mock_task_processing_service,
    mock_uow,
    mock_task_registry,
    mock_task_plugin_type,
    mock_task_plugin,
):
    """Terminal or cancelled tasks should not execute a plugin."""

    mock_uow.workflow_executions.start_task.return_value = None

    result = mock_task_processing_service.process(uuid4())

    assert result.enqueue_task_ids == []
    assert result.should_retry is False

    mock_task_registry.get.assert_not_called()
    mock_task_plugin_type.assert_not_called()
    mock_task_plugin.execute.assert_not_called()
    mock_uow.workflow_executions.complete_task.assert_not_called()
    mock_uow.workflow_executions.retry_task.assert_not_called()


# ==================================================================================================
# Unexpected Failures
# ==================================================================================================


def test_process_propagates_plugin_exception(
    mock_task_processing_service,
    start_task_result_factory,
    mock_uow,
    mock_task_plugin,
):
    """Unexpected plugin exceptions should propagate without recording a result."""

    mock_uow.workflow_executions.start_task.return_value = start_task_result_factory()
    mock_task_plugin.execute.side_effect = RuntimeError("Unexpected plugin error.")

    with pytest.raises(
        RuntimeError,
        match="Unexpected plugin error",
    ):
        mock_task_processing_service.process(uuid4())

    mock_uow.workflow_executions.complete_task.assert_not_called()
    mock_uow.workflow_executions.retry_task.assert_not_called()


def test_process_propagates_unknown_plugin(
    mock_task_processing_service,
    start_task_result_factory,
    mock_uow,
    mock_task_registry,
    mock_task_plugin_type,
    mock_task_plugin,
):
    """Unknown plugin types should propagate the registry error."""

    task = start_task_result_factory(
        plugin_type="unknown_task",
    )
    mock_uow.workflow_executions.start_task.return_value = task

    mock_task_registry.get.side_effect = KeyError("Unknown plugin type 'unknown_task'.")

    with pytest.raises(
        KeyError,
        match="Unknown plugin type",
    ):
        mock_task_processing_service.process(uuid4())

    mock_task_plugin_type.assert_not_called()
    mock_task_plugin.execute.assert_not_called()
    mock_uow.workflow_executions.complete_task.assert_not_called()
    mock_uow.workflow_executions.retry_task.assert_not_called()


# ==================================================================================================
# Transaction Boundaries
# ==================================================================================================


def test_process_commits_start_before_plugin_execution(
    mock_task_processing_service,
    start_task_result_factory,
    successful_task_result_factory,
    mock_uow,
    mock_task_plugin,
):
    """The running state should commit before arbitrary plugin execution."""

    events = []

    mock_uow.workflow_executions.start_task.return_value = start_task_result_factory()
    mock_uow.workflow_executions.complete_task.return_value = CompleteTaskExecutionResult(
        runnable_task_execution_ids=[],
        workflow_completed=False,
    )

    mock_uow.commit.side_effect = lambda: events.append("commit")
    mock_task_plugin.execute.side_effect = lambda context: (
        events.append("execute") or successful_task_result_factory()
    )

    mock_task_processing_service.process(uuid4())

    assert events == [
        "commit",
        "execute",
        "commit",
    ]


def test_process_uses_separate_units_of_work_for_start_and_completion(
    start_task_result_factory,
    successful_task_result_factory,
    mock_task_registry,
    mock_task_plugin,
):
    """Starting and completing a task should use separate units of work."""

    start_uow = MagicMock()
    start_uow.__enter__.return_value = start_uow
    start_uow.__exit__.return_value = None
    start_uow.workflow_executions.start_task.return_value = start_task_result_factory()

    completion_uow = MagicMock()
    completion_uow.__enter__.return_value = completion_uow
    completion_uow.__exit__.return_value = None
    completion_uow.workflow_executions.complete_task.return_value = CompleteTaskExecutionResult(
        runnable_task_execution_ids=[],
        workflow_completed=False,
    )

    uow_factory = MagicMock(
        side_effect=[
            start_uow,
            completion_uow,
        ]
    )

    mock_task_plugin.execute.return_value = successful_task_result_factory()

    service = TaskProcessingService(
        uow_factory=uow_factory,
        task_registry=mock_task_registry,
    )

    service.process(uuid4())

    assert uow_factory.call_count == 2

    start_uow.workflow_executions.start_task.assert_called_once()
    start_uow.workflow_executions.complete_task.assert_not_called()

    completion_uow.workflow_executions.start_task.assert_not_called()
    completion_uow.workflow_executions.complete_task.assert_called_once()

    start_uow.commit.assert_called_once_with()
    completion_uow.commit.assert_called_once_with()


def test_process_uses_separate_units_of_work_for_start_and_retry(
    start_task_result_factory,
    failed_task_result_factory,
    mock_task_registry,
    mock_task_plugin,
):
    """Starting and retrying a task should use separate units of work."""

    start_uow = MagicMock()
    start_uow.__enter__.return_value = start_uow
    start_uow.__exit__.return_value = None
    start_uow.workflow_executions.start_task.return_value = start_task_result_factory()

    retry_uow = MagicMock()
    retry_uow.__enter__.return_value = retry_uow
    retry_uow.__exit__.return_value = None
    retry_uow.workflow_executions.retry_task.return_value = RetryTaskExecutionResult(
        should_retry=True,
        workflow_failed=False,
    )

    uow_factory = MagicMock(
        side_effect=[
            start_uow,
            retry_uow,
        ]
    )

    mock_task_plugin.execute.return_value = failed_task_result_factory()

    service = TaskProcessingService(
        uow_factory=uow_factory,
        task_registry=mock_task_registry,
    )

    service.process(uuid4())

    assert uow_factory.call_count == 2

    start_uow.workflow_executions.start_task.assert_called_once()
    start_uow.workflow_executions.retry_task.assert_not_called()

    retry_uow.workflow_executions.start_task.assert_not_called()
    retry_uow.workflow_executions.retry_task.assert_called_once()

    start_uow.commit.assert_called_once_with()
    retry_uow.commit.assert_called_once_with()


def test_process_does_not_commit_when_task_is_unprocessable(
    mock_task_processing_service,
    mock_uow,
):
    """An unprocessable task should not commit a start transition."""

    mock_uow.workflow_executions.start_task.return_value = None

    mock_task_processing_service.process(uuid4())

    mock_uow.commit.assert_not_called()
