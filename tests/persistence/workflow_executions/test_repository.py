"""
Tests for the workflow execution repository.
"""

from uuid import uuid4

from sqlalchemy.orm import Session

from automation_platform.persistence.workflow_definitions import (
    WorkflowDefinitionRepository,
)
from automation_platform.persistence.workflow_executions import (
    WorkflowExecutionRepository,
)


def test_load_returns_none_when_workflow_does_not_exist(session: Session) -> None:
    """Loading an unknown workflow returns None."""

    repository = WorkflowExecutionRepository(session)

    assert repository.load(uuid4()) is None


def test_save_and_load_workflow_execution(
    session: Session,
    persisted_workflow_definition,
    workflow_execution_factory,
) -> None:
    """Workflow executions round-trip through persistence."""

    execution = workflow_execution_factory(
        workflow_definition=persisted_workflow_definition,
    )

    repository = WorkflowExecutionRepository(session)

    repository.save(execution)
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

    repository.save(execution)
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

    repository.save(execution)
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


def test_save_and_load_multiple_task_executions(
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

    repository.save(execution)
    session.commit()

    loaded = repository.load(execution.id)

    assert loaded == execution


def test_save_and_load_child_task_ids(
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

    repository.save(execution)
    session.commit()

    loaded = repository.load(execution.id)

    assert loaded == execution


def test_save_persists_task_executions(
    session: Session,
    persisted_workflow_definition,
    workflow_execution_factory,
) -> None:
    """Saving a workflow also persists its owned task executions."""

    execution = workflow_execution_factory(
        workflow_definition=persisted_workflow_definition,
    )

    repository = WorkflowExecutionRepository(session)

    repository.save(execution)
    session.commit()

    loaded = repository.load(execution.id)

    assert len(loaded.task_executions) == len(execution.task_executions)


def test_update_task_execution(
    session: Session,
    persisted_workflow_definition,
    workflow_execution_factory,
) -> None:
    """Task execution updates are persisted."""

    execution = workflow_execution_factory(
        workflow_definition=persisted_workflow_definition,
    )

    repository = WorkflowExecutionRepository(session)

    repository.save(execution)
    session.commit()

    task = execution.task_executions[0]

    task.retry_count = 5
    task.remaining_dependencies = 2
    task.error_message = "Failure"

    repository.save(execution)
    session.commit()

    loaded = repository.load(execution.id)

    assert loaded == execution
