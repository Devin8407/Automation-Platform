"""
Tests for the workflow execution repository.
"""

from datetime import UTC, datetime
from uuid import uuid4

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

    assert repository.start_task(task.id, started_at)

    session.commit()

    loaded = repository.load(execution.id)
    loaded_task = loaded.task_executions[0]

    assert loaded_task.status == TaskStatus.RUNNING
    assert loaded_task.started_at == started_at


def test_start_task_returns_false_when_task_is_not_pending(
    session: Session,
    persisted_workflow_definition,
    workflow_execution_factory,
) -> None:
    """Only pending task executions may be started."""

    execution = workflow_execution_factory(
        workflow_definition=persisted_workflow_definition,
    )

    task = execution.task_executions[0]
    task.status = TaskStatus.RUNNING

    repository = WorkflowExecutionRepository(session)

    repository.create(execution)
    session.commit()

    started_at = datetime.now(UTC)

    assert not repository.start_task(task.id, started_at)

    session.commit()

    loaded = repository.load(execution.id)

    loaded_task = loaded.task_executions[0]

    assert loaded_task.status == TaskStatus.RUNNING
    assert loaded_task.started_at is None


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


def test_complete_task_returns_false_when_task_not_running(
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


# ==============================================================================
# retry_task()
# ==============================================================================


def test_retry_task_decrements_remaining_tries(
    session: Session,
    persisted_workflow_definition,
    workflow_execution_factory,
) -> None:
    """Retrying a task with remaining retries returns it to the pending state."""

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

    assert loaded_task.status == TaskStatus.PENDING
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


def test_retry_task_returns_false_when_task_not_running(
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
