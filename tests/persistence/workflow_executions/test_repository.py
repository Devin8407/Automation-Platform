"""
Tests for the workflow execution repository.
"""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from automation_platform.domain.common.enums import (
    TaskStatus,
    WorkflowStatus,
)
from automation_platform.domain.execution_runtime import TaskOutput
from automation_platform.persistence.workflow_definitions import (
    WorkflowDefinitionRepository,
)
from automation_platform.persistence.workflow_executions import (
    WorkflowExecutionRepository,
)
from automation_platform.persistence.workflow_executions.operations import (
    CompleteTaskExecutionRequest,
    RetryTaskExecutionRequest,
)


def test_load_returns_none_when_workflow_does_not_exist(
    session: Session,
) -> None:
    """Loading an unknown workflow returns None."""

    repository = WorkflowExecutionRepository(session)

    assert repository.load(uuid4()) is None


def test_create_and_load_workflow_execution(
    session: Session,
    persisted_workflow_definition,
    workflow_execution_factory,
) -> None:
    """Workflow executions round-trip through persistence."""

    execution = workflow_execution_factory(
        workflow_definition=persisted_workflow_definition,
    )

    repository = WorkflowExecutionRepository(session)

    repository.create(execution)
    session.commit()

    loaded = repository.load(execution.id)

    assert loaded == execution


def test_delete_workflow_execution(
    session: Session,
    persisted_workflow_definition,
    workflow_execution_factory,
) -> None:
    """Deleting a workflow execution removes it."""

    execution = workflow_execution_factory(
        workflow_definition=persisted_workflow_definition,
    )

    repository = WorkflowExecutionRepository(session)

    repository.create(execution)
    session.commit()

    repository.delete(execution.id)
    session.commit()

    assert repository.load(execution.id) is None


def test_find_workflow_execution(
    session: Session,
    persisted_workflow_definition,
    workflow_execution_factory,
) -> None:
    """The owning workflow execution can be found from a task execution."""

    execution = workflow_execution_factory(
        workflow_definition=persisted_workflow_definition,
    )

    repository = WorkflowExecutionRepository(session)

    repository.create(execution)
    session.commit()

    task = execution.task_executions[0]

    workflow_execution_id = repository.find_workflow_execution(task.id)

    assert workflow_execution_id == execution.id


def test_find_workflow_execution_returns_none_when_task_does_not_exist(
    session: Session,
) -> None:
    """Unknown task executions return None."""

    repository = WorkflowExecutionRepository(session)

    assert repository.find_workflow_execution(uuid4()) is None


def test_create_and_load_multiple_task_executions(
    session: Session,
    workflow_definition_factory,
    task_definition_factory,
    workflow_execution_factory,
) -> None:
    """Task executions are persisted with their workflow."""

    task1 = task_definition_factory(key="extract")
    task2 = task_definition_factory(key="transform")
    task3 = task_definition_factory(key="load")

    definition = workflow_definition_factory(
        task_definitions=[task1, task2, task3],
    )

    WorkflowDefinitionRepository(session).save(definition)
    session.commit()

    execution = workflow_execution_factory(
        workflow_definition=definition,
    )

    repository = WorkflowExecutionRepository(session)

    repository.create(execution)
    session.commit()

    loaded = repository.load(execution.id)

    assert loaded == execution


def test_create_and_load_child_task_ids(
    session: Session,
    workflow_definition_factory,
    task_definition_factory,
    workflow_execution_factory,
) -> None:
    """Child task identifiers survive persistence."""

    parent_definition = task_definition_factory(key="parent")
    child_definition = task_definition_factory(key="child")

    definition = workflow_definition_factory(
        task_definitions=[
            parent_definition,
            child_definition,
        ],
    )

    WorkflowDefinitionRepository(session).save(definition)
    session.commit()

    execution = workflow_execution_factory(
        workflow_definition=definition,
    )

    parent = execution.task_executions[0]
    child = execution.task_executions[1]

    parent.child_task_ids = [child.id]

    repository = WorkflowExecutionRepository(session)

    repository.create(execution)
    session.commit()

    loaded = repository.load(execution.id)

    assert loaded == execution


# ==============================================================================
# start_task()
# ==============================================================================


def test_start_task_starts_pending_task(
    session: Session,
    persisted_workflow_definition,
    workflow_execution_factory,
) -> None:
    """Pending task executions can be started."""

    execution = workflow_execution_factory(
        workflow_definition=persisted_workflow_definition,
    )

    repository = WorkflowExecutionRepository(session)

    repository.create(execution)
    session.commit()

    task = execution.task_executions[0]
    started_at = datetime.now(UTC)

    result = repository.start_task(task.id, started_at)

    session.commit()

    assert result is not None
    assert result.plugin_type == task.plugin_type
    assert result.configuration == task.configuration
    assert result.parent_outputs == {}

    loaded = repository.load(execution.id)
    loaded_task = loaded.task_executions[0]

    assert loaded_task.status == TaskStatus.RUNNING
    assert loaded_task.started_at == started_at


def test_start_task_returns_running_task(
    session: Session,
    persisted_workflow_definition,
    workflow_execution_factory,
) -> None:
    """Running task executions can be reclaimed."""

    execution = workflow_execution_factory(
        workflow_definition=persisted_workflow_definition,
    )

    task = execution.task_executions[0]
    task.status = TaskStatus.RUNNING
    task.started_at = datetime.now(UTC)

    repository = WorkflowExecutionRepository(session)

    repository.create(execution)
    session.commit()

    original_started_at = task.started_at

    result = repository.start_task(
        task.id,
        datetime.now(UTC),
    )

    session.commit()

    assert result is not None
    assert result.plugin_type == task.plugin_type
    assert result.configuration == task.configuration
    assert result.parent_outputs == {}

    loaded = repository.load(execution.id)
    loaded_task = loaded.task_executions[0]

    assert loaded_task.status == TaskStatus.RUNNING
    assert loaded_task.started_at == original_started_at


def test_start_task_returns_none_when_task_is_terminal(
    session: Session,
    persisted_workflow_definition,
    workflow_execution_factory,
) -> None:
    """Terminal task executions cannot be started."""

    execution = workflow_execution_factory(
        workflow_definition=persisted_workflow_definition,
    )

    task = execution.task_executions[0]
    task.status = TaskStatus.COMPLETED

    repository = WorkflowExecutionRepository(session)

    repository.create(execution)
    session.commit()

    result = repository.start_task(
        task.id,
        datetime.now(UTC),
    )

    session.commit()

    assert result is None

    loaded = repository.load(execution.id)
    loaded_task = loaded.task_executions[0]

    assert loaded_task.status == TaskStatus.COMPLETED


def test_start_task_returns_none_when_task_does_not_exist(
    session: Session,
) -> None:
    """Unknown task executions cannot be started."""

    repository = WorkflowExecutionRepository(session)

    result = repository.start_task(
        uuid4(),
        datetime.now(UTC),
    )

    assert result is None


def test_start_task_returns_parent_outputs(
    session: Session,
    workflow_definition_factory,
    task_definition_factory,
    workflow_execution_factory,
) -> None:
    """Parent task outputs are returned when starting a child task."""

    parent_definition = task_definition_factory(key="parent")
    child_definition = task_definition_factory(key="child")

    definition = workflow_definition_factory(
        task_definitions=[
            parent_definition,
            child_definition,
        ],
    )

    WorkflowDefinitionRepository(session).save(definition)
    session.commit()

    execution = workflow_execution_factory(
        workflow_definition=definition,
    )

    parent = execution.task_executions[0]
    child = execution.task_executions[1]

    parent.status = TaskStatus.COMPLETED
    parent.output = TaskOutput({"value": 123})

    child.parent_task_ids = [parent.id]

    repository = WorkflowExecutionRepository(session)

    repository.create(execution)
    session.commit()

    result = repository.start_task(
        child.id,
        datetime.now(UTC),
    )

    assert result is not None
    assert result.parent_outputs == {
        parent.key: TaskOutput({"value": 123}),
    }


def test_start_task_raises_when_parent_has_no_output(
    session: Session,
    workflow_definition_factory,
    task_definition_factory,
    workflow_execution_factory,
) -> None:
    """Starting a child fails when a parent has no output."""

    parent_definition = task_definition_factory(key="parent")
    child_definition = task_definition_factory(key="child")

    definition = workflow_definition_factory(
        task_definitions=[
            parent_definition,
            child_definition,
        ],
    )

    WorkflowDefinitionRepository(session).save(definition)
    session.commit()

    execution = workflow_execution_factory(
        workflow_definition=definition,
    )

    parent = execution.task_executions[0]
    child = execution.task_executions[1]

    parent.status = TaskStatus.COMPLETED
    parent.output = None

    child.parent_task_ids = [parent.id]

    repository = WorkflowExecutionRepository(session)

    repository.create(execution)
    session.commit()

    with pytest.raises(
        RuntimeError,
        match="does not have an output",
    ):
        repository.start_task(
            child.id,
            datetime.now(UTC),
        )


def test_start_task_returns_multiple_parent_outputs(
    session: Session,
    workflow_definition_factory,
    task_definition_factory,
    workflow_execution_factory,
) -> None:
    """Outputs from all parent tasks are returned when starting a child task."""

    parent1_definition = task_definition_factory(key="parent1")
    parent2_definition = task_definition_factory(key="parent2")
    child_definition = task_definition_factory(key="child")

    definition = workflow_definition_factory(
        task_definitions=[
            parent1_definition,
            parent2_definition,
            child_definition,
        ],
    )

    WorkflowDefinitionRepository(session).save(definition)
    session.commit()

    execution = workflow_execution_factory(
        workflow_definition=definition,
    )

    parent1 = execution.task_executions[0]
    parent2 = execution.task_executions[1]
    child = execution.task_executions[2]

    parent1.status = TaskStatus.COMPLETED
    parent1.output = TaskOutput({"value": 1})

    parent2.status = TaskStatus.COMPLETED
    parent2.output = TaskOutput({"value": 2})

    child.parent_task_ids = [
        parent1.id,
        parent2.id,
    ]

    repository = WorkflowExecutionRepository(session)

    repository.create(execution)
    session.commit()

    result = repository.start_task(
        child.id,
        datetime.now(UTC),
    )

    assert result is not None
    assert result.parent_outputs == {
        parent1.key: TaskOutput({"value": 1}),
        parent2.key: TaskOutput({"value": 2}),
    }


# ==============================================================================
# complete_task()
# ==============================================================================


def test_complete_task_marks_task_completed(
    session: Session,
    persisted_workflow_definition,
    workflow_execution_factory,
) -> None:
    """Running task executions can be completed."""

    execution = workflow_execution_factory(
        workflow_definition=persisted_workflow_definition,
        status=WorkflowStatus.RUNNING,
    )

    task = execution.task_executions[0]
    task.status = TaskStatus.RUNNING

    repository = WorkflowExecutionRepository(session)

    repository.create(execution)
    session.commit()

    completed_at = datetime.now(UTC)

    result = repository.complete_task(
        CompleteTaskExecutionRequest(
            task_execution_id=task.id,
            output=TaskOutput({"value": 123}),
            completed_at=completed_at,
        )
    )

    session.commit()

    loaded = repository.load(execution.id)
    loaded_task = loaded.task_executions[0]

    assert loaded_task.status == TaskStatus.COMPLETED
    assert loaded_task.output == TaskOutput({"value": 123})
    assert loaded_task.completed_at == completed_at
    assert result.runnable_task_execution_ids == []
    assert result.workflow_completed


def test_complete_task_does_nothing_when_task_not_running(
    session: Session,
    persisted_workflow_definition,
    workflow_execution_factory,
) -> None:
    """Completing a non-running task has no effect."""

    execution = workflow_execution_factory(
        workflow_definition=persisted_workflow_definition,
        status=WorkflowStatus.RUNNING,
    )

    repository = WorkflowExecutionRepository(session)

    repository.create(execution)
    session.commit()

    task = execution.task_executions[0]

    result = repository.complete_task(
        CompleteTaskExecutionRequest(
            task_execution_id=task.id,
            output=TaskOutput(),
            completed_at=datetime.now(UTC),
        )
    )

    session.commit()

    loaded = repository.load(execution.id)

    assert loaded == execution
    assert result.runnable_task_execution_ids == []
    assert not result.workflow_completed


def test_complete_task_releases_child_when_last_dependency_completed(
    session: Session,
    workflow_definition_factory,
    task_definition_factory,
    workflow_execution_factory,
) -> None:
    """Completing the final parent dependency releases the child."""

    parent_definition = task_definition_factory(key="parent")
    child_definition = task_definition_factory(key="child")

    definition = workflow_definition_factory(
        task_definitions=[
            parent_definition,
            child_definition,
        ]
    )

    WorkflowDefinitionRepository(session).save(definition)
    session.commit()

    execution = workflow_execution_factory(
        workflow_definition=definition,
        status=WorkflowStatus.RUNNING,
    )

    parent = execution.task_executions[0]
    child = execution.task_executions[1]

    parent.status = TaskStatus.RUNNING
    parent.child_task_ids = [child.id]

    child.remaining_dependencies = 1

    repository = WorkflowExecutionRepository(session)

    repository.create(execution)
    session.commit()

    result = repository.complete_task(
        CompleteTaskExecutionRequest(
            task_execution_id=parent.id,
            output=TaskOutput(),
            completed_at=datetime.now(UTC),
        )
    )

    session.commit()

    loaded = repository.load(execution.id)

    loaded_child = next(task for task in loaded.task_executions if task.id == child.id)

    assert loaded_child.remaining_dependencies == 0
    assert result.runnable_task_execution_ids == [child.id]


def test_complete_task_does_not_release_child_when_dependencies_remain(
    session: Session,
    workflow_definition_factory,
    task_definition_factory,
    workflow_execution_factory,
) -> None:
    """Children remain blocked while dependencies remain."""

    parent_definition = task_definition_factory(key="parent")
    child_definition = task_definition_factory(key="child")

    definition = workflow_definition_factory(
        task_definitions=[
            parent_definition,
            child_definition,
        ]
    )

    WorkflowDefinitionRepository(session).save(definition)
    session.commit()

    execution = workflow_execution_factory(
        workflow_definition=definition,
        status=WorkflowStatus.RUNNING,
    )

    parent = execution.task_executions[0]
    child = execution.task_executions[1]

    parent.status = TaskStatus.RUNNING
    parent.child_task_ids = [child.id]

    child.remaining_dependencies = 2

    repository = WorkflowExecutionRepository(session)

    repository.create(execution)
    session.commit()

    result = repository.complete_task(
        CompleteTaskExecutionRequest(
            task_execution_id=parent.id,
            output=TaskOutput(),
            completed_at=datetime.now(UTC),
        )
    )

    session.commit()

    loaded = repository.load(execution.id)

    loaded_child = next(task for task in loaded.task_executions if task.id == child.id)

    assert loaded_child.remaining_dependencies == 1
    assert result.runnable_task_execution_ids == []


def test_complete_task_completes_workflow_when_last_task_finishes(
    session: Session,
    persisted_workflow_definition,
    workflow_execution_factory,
) -> None:
    """The workflow completes when its last task completes."""

    execution = workflow_execution_factory(
        workflow_definition=persisted_workflow_definition,
        status=WorkflowStatus.RUNNING,
    )

    task = execution.task_executions[0]
    task.status = TaskStatus.RUNNING

    repository = WorkflowExecutionRepository(session)

    repository.create(execution)
    session.commit()

    completed_at = datetime.now(UTC)

    result = repository.complete_task(
        CompleteTaskExecutionRequest(
            task_execution_id=task.id,
            output=TaskOutput(),
            completed_at=completed_at,
        )
    )

    session.commit()

    loaded = repository.load(execution.id)

    assert loaded.status == WorkflowStatus.COMPLETED
    assert loaded.completed_at == completed_at
    assert result.workflow_completed


def test_complete_task_does_not_complete_workflow_when_tasks_remain(
    session: Session,
    workflow_definition_factory,
    task_definition_factory,
    workflow_execution_factory,
) -> None:
    """The workflow remains running while unfinished tasks exist."""

    task1 = task_definition_factory(key="task1")
    task2 = task_definition_factory(key="task2")

    definition = workflow_definition_factory(
        task_definitions=[task1, task2],
    )

    WorkflowDefinitionRepository(session).save(definition)
    session.commit()

    execution = workflow_execution_factory(
        workflow_definition=definition,
        status=WorkflowStatus.RUNNING,
    )

    execution.task_executions[0].status = TaskStatus.RUNNING

    repository = WorkflowExecutionRepository(session)

    repository.create(execution)
    session.commit()

    result = repository.complete_task(
        CompleteTaskExecutionRequest(
            task_execution_id=execution.task_executions[0].id,
            output=TaskOutput(),
            completed_at=datetime.now(UTC),
        )
    )

    session.commit()

    loaded = repository.load(execution.id)

    assert loaded.status == WorkflowStatus.RUNNING
    assert loaded.completed_at is None
    assert not result.workflow_completed


def test_complete_task_does_nothing_when_task_does_not_exist(
    session: Session,
) -> None:
    """Completing an unknown task has no effect."""

    repository = WorkflowExecutionRepository(session)

    result = repository.complete_task(
        CompleteTaskExecutionRequest(
            task_execution_id=uuid4(),
            output=TaskOutput(),
            completed_at=datetime.now(UTC),
        )
    )

    assert result.runnable_task_execution_ids == []
    assert not result.workflow_completed


# ==============================================================================
# retry_task()
# ==============================================================================


def test_retry_task_keeps_task_running_when_retries_remain(
    session: Session,
    persisted_workflow_definition,
    workflow_execution_factory,
) -> None:
    """Retrying a task keeps it running when retries remain."""

    execution = workflow_execution_factory(
        workflow_definition=persisted_workflow_definition,
        status=WorkflowStatus.RUNNING,
    )

    task = execution.task_executions[0]
    task.status = TaskStatus.RUNNING
    task.remaining_tries = 3

    repository = WorkflowExecutionRepository(session)

    repository.create(execution)
    session.commit()

    result = repository.retry_task(
        RetryTaskExecutionRequest(
            task_execution_id=task.id,
            error_message="Temporary failure",
            completed_at=datetime.now(UTC),
        )
    )

    session.commit()

    loaded = repository.load(execution.id)
    loaded_task = loaded.task_executions[0]

    assert loaded_task.status == TaskStatus.RUNNING
    assert loaded_task.remaining_tries == 2
    assert loaded_task.error_message == "Temporary failure"
    assert loaded_task.completed_at is None

    assert result.should_retry
    assert not result.workflow_failed


def test_retry_task_fails_task_when_last_retry_used(
    session: Session,
    persisted_workflow_definition,
    workflow_execution_factory,
) -> None:
    """Exhausting retries marks the task as failed."""

    execution = workflow_execution_factory(
        workflow_definition=persisted_workflow_definition,
        status=WorkflowStatus.RUNNING,
    )

    task = execution.task_executions[0]
    task.status = TaskStatus.RUNNING
    task.remaining_tries = 1

    repository = WorkflowExecutionRepository(session)

    repository.create(execution)
    session.commit()

    completed_at = datetime.now(UTC)

    result = repository.retry_task(
        RetryTaskExecutionRequest(
            task_execution_id=task.id,
            error_message="Permanent failure",
            completed_at=completed_at,
        )
    )

    session.commit()

    loaded = repository.load(execution.id)
    loaded_task = loaded.task_executions[0]

    assert loaded_task.status == TaskStatus.FAILED
    assert loaded_task.remaining_tries == 0
    assert loaded_task.error_message == "Permanent failure"
    assert loaded_task.completed_at == completed_at

    assert not result.should_retry


def test_retry_task_fails_workflow_when_retries_exhausted(
    session: Session,
    persisted_workflow_definition,
    workflow_execution_factory,
) -> None:
    """Exhausting retries also fails the workflow execution."""

    execution = workflow_execution_factory(
        workflow_definition=persisted_workflow_definition,
        status=WorkflowStatus.RUNNING,
    )

    task = execution.task_executions[0]
    task.status = TaskStatus.RUNNING
    task.remaining_tries = 1

    repository = WorkflowExecutionRepository(session)

    repository.create(execution)
    session.commit()

    completed_at = datetime.now(UTC)

    result = repository.retry_task(
        RetryTaskExecutionRequest(
            task_execution_id=task.id,
            error_message="Permanent failure",
            completed_at=completed_at,
        )
    )

    session.commit()

    loaded = repository.load(execution.id)

    assert loaded.status == WorkflowStatus.FAILED
    assert loaded.completed_at == completed_at

    assert not result.should_retry
    assert result.workflow_failed


def test_retry_task_cancels_remaining_tasks_when_workflow_fails(
    session: Session,
    workflow_definition_factory,
    task_definition_factory,
    workflow_execution_factory,
) -> None:
    """Failing a workflow cancels its remaining unfinished tasks."""

    failing_definition = task_definition_factory(key="failing")
    pending_definition = task_definition_factory(key="pending")
    running_definition = task_definition_factory(key="running")
    completed_definition = task_definition_factory(key="completed")

    definition = workflow_definition_factory(
        task_definitions=[
            failing_definition,
            pending_definition,
            running_definition,
            completed_definition,
        ],
    )

    WorkflowDefinitionRepository(session).save(definition)
    session.commit()

    execution = workflow_execution_factory(
        workflow_definition=definition,
        status=WorkflowStatus.RUNNING,
    )

    failing_task = execution.task_executions[0]
    pending_task = execution.task_executions[1]
    running_task = execution.task_executions[2]
    completed_task = execution.task_executions[3]

    failing_task.status = TaskStatus.RUNNING
    failing_task.remaining_tries = 1

    pending_task.status = TaskStatus.PENDING
    running_task.status = TaskStatus.RUNNING

    completed_at_before_failure = datetime.now(UTC)
    completed_task.status = TaskStatus.COMPLETED
    completed_task.completed_at = completed_at_before_failure

    repository = WorkflowExecutionRepository(session)

    repository.create(execution)
    session.commit()

    completed_at = datetime.now(UTC)

    result = repository.retry_task(
        RetryTaskExecutionRequest(
            task_execution_id=failing_task.id,
            error_message="Permanent failure",
            completed_at=completed_at,
        )
    )

    session.commit()

    loaded = repository.load(execution.id)

    loaded_tasks = {task.id: task for task in loaded.task_executions}

    loaded_failing_task = loaded_tasks[failing_task.id]
    loaded_pending_task = loaded_tasks[pending_task.id]
    loaded_running_task = loaded_tasks[running_task.id]
    loaded_completed_task = loaded_tasks[completed_task.id]

    assert loaded_failing_task.status == TaskStatus.FAILED
    assert loaded_failing_task.remaining_tries == 0
    assert loaded_failing_task.error_message == "Permanent failure"
    assert loaded_failing_task.completed_at == completed_at

    assert loaded_pending_task.status == TaskStatus.CANCELLED
    assert loaded_pending_task.completed_at == completed_at

    assert loaded_running_task.status == TaskStatus.CANCELLED
    assert loaded_running_task.completed_at == completed_at

    assert loaded_completed_task.status == TaskStatus.COMPLETED
    assert loaded_completed_task.completed_at == completed_at_before_failure

    assert loaded.status == WorkflowStatus.FAILED
    assert loaded.completed_at == completed_at

    assert not result.should_retry
    assert result.workflow_failed


def test_retry_task_does_nothing_when_task_not_running(
    session: Session,
    persisted_workflow_definition,
    workflow_execution_factory,
) -> None:
    """Retrying a non-running task has no effect."""

    execution = workflow_execution_factory(
        workflow_definition=persisted_workflow_definition,
        status=WorkflowStatus.RUNNING,
    )

    task = execution.task_executions[0]
    task.status = TaskStatus.COMPLETED
    task.remaining_tries = 3

    repository = WorkflowExecutionRepository(session)

    repository.create(execution)
    session.commit()

    result = repository.retry_task(
        RetryTaskExecutionRequest(
            task_execution_id=task.id,
            error_message="Ignored",
            completed_at=datetime.now(UTC),
        )
    )

    session.commit()

    loaded = repository.load(execution.id)

    assert loaded == execution

    assert not result.should_retry
    assert not result.workflow_failed


def test_retry_task_does_nothing_when_no_retries_remain(
    session: Session,
    persisted_workflow_definition,
    workflow_execution_factory,
) -> None:
    """Retrying a task with no remaining retries has no effect."""

    execution = workflow_execution_factory(
        workflow_definition=persisted_workflow_definition,
        status=WorkflowStatus.RUNNING,
    )

    task = execution.task_executions[0]
    task.status = TaskStatus.RUNNING
    task.remaining_tries = 0

    repository = WorkflowExecutionRepository(session)

    repository.create(execution)
    session.commit()

    result = repository.retry_task(
        RetryTaskExecutionRequest(
            task_execution_id=task.id,
            error_message="Ignored",
            completed_at=datetime.now(UTC),
        )
    )

    session.commit()

    loaded = repository.load(execution.id)

    assert loaded == execution

    assert not result.should_retry
    assert not result.workflow_failed


def test_retry_task_does_nothing_when_task_does_not_exist(
    session: Session,
) -> None:
    """Retrying an unknown task has no effect."""

    repository = WorkflowExecutionRepository(session)

    result = repository.retry_task(
        RetryTaskExecutionRequest(
            task_execution_id=uuid4(),
            error_message="Ignored",
            completed_at=datetime.now(UTC),
        )
    )

    assert not result.should_retry
    assert not result.workflow_failed
