"""Tests for the workflow start application service."""

from uuid import UUID

import pytest

from automation_platform.application.exceptions import (
    WorkflowDefinitionDisabledError,
    WorkflowDefinitionNotFoundError,
)
from automation_platform.domain import TaskStatus, WorkflowExecution, WorkflowStatus

# ==================================================================================================
# Successful Start
# ==================================================================================================


def test_start_creates_and_persists_workflow_execution(
    mock_workflow_start_service,
    workflow_definition_factory,
    mock_uow,
):
    """Starting a workflow should create and persist a running execution."""

    workflow_definition = workflow_definition_factory()
    mock_uow.workflow_definitions.load.return_value = workflow_definition

    workflow_execution_id = mock_workflow_start_service.start(workflow_definition.id)

    mock_uow.workflow_definitions.load.assert_called_once_with(workflow_definition.id)
    mock_uow.workflow_executions.create.assert_called_once()

    workflow_execution = mock_uow.workflow_executions.create.call_args.args[0]

    assert isinstance(workflow_execution, WorkflowExecution)
    assert workflow_execution.id == workflow_execution_id
    assert isinstance(workflow_execution_id, UUID)
    assert workflow_execution.workflow_definition_id == workflow_definition.id
    assert workflow_execution.status is WorkflowStatus.RUNNING

    mock_uow.commit.assert_called_once_with()


def test_start_creates_task_execution_from_definition(
    mock_workflow_start_service,
    task_definition_factory,
    workflow_definition_factory,
    mock_uow,
):
    """Starting a workflow should compile task definitions into task executions."""

    task_definition = task_definition_factory(
        plugin_type="test_task",
        key="task_a",
        configuration={"value": 42},
        max_tries=3,
    )
    workflow_definition = workflow_definition_factory(task_definitions=[task_definition])

    mock_uow.workflow_definitions.load.return_value = workflow_definition

    mock_workflow_start_service.start(workflow_definition.id)

    workflow_execution = mock_uow.workflow_executions.create.call_args.args[0]
    task_execution = workflow_execution.task_executions[0]

    assert task_execution.id != task_definition.id
    assert task_execution.workflow_execution_id == workflow_execution.id
    assert task_execution.task_definition_id == task_definition.id

    assert task_execution.plugin_type == "test_task"
    assert task_execution.configuration == {"value": 42}

    assert task_execution.status is TaskStatus.PENDING
    assert task_execution.remaining_dependencies == 0
    assert task_execution.remaining_tries == 3

    assert task_execution.parent_task_ids == []
    assert task_execution.child_task_ids == []


def test_start_creates_execution_graph(
    mock_workflow_start_service,
    task_definition_factory,
    workflow_definition_factory,
    mock_uow,
):
    """Starting a workflow should compile definition dependencies into an execution graph."""

    task_a = task_definition_factory(key="task_a")
    task_b = task_definition_factory(key="task_b")

    task_c = task_definition_factory(
        key="task_c",
        dependencies=[task_a.id, task_b.id],
    )
    task_d = task_definition_factory(
        key="task_d",
        dependencies=[task_b.id],
    )
    task_e = task_definition_factory(
        key="task_e",
        dependencies=[task_c.id, task_d.id],
    )

    workflow_definition = workflow_definition_factory(
        task_definitions=[
            task_a,
            task_b,
            task_c,
            task_d,
            task_e,
        ]
    )

    mock_uow.workflow_definitions.load.return_value = workflow_definition

    mock_workflow_start_service.start(workflow_definition.id)

    workflow_execution = mock_uow.workflow_executions.create.call_args.args[0]

    executions = {
        task_execution.task_definition_id: task_execution
        for task_execution in workflow_execution.task_executions
    }

    execution_a = executions[task_a.id]
    execution_b = executions[task_b.id]
    execution_c = executions[task_c.id]
    execution_d = executions[task_d.id]
    execution_e = executions[task_e.id]

    assert execution_a.parent_task_ids == []
    assert execution_a.child_task_ids == [execution_c.id]
    assert execution_a.remaining_dependencies == 0

    assert execution_b.parent_task_ids == []
    assert set(execution_b.child_task_ids) == {
        execution_c.id,
        execution_d.id,
    }
    assert execution_b.remaining_dependencies == 0

    assert set(execution_c.parent_task_ids) == {
        execution_a.id,
        execution_b.id,
    }
    assert execution_c.child_task_ids == [execution_e.id]
    assert execution_c.remaining_dependencies == 2

    assert execution_d.parent_task_ids == [execution_b.id]
    assert execution_d.child_task_ids == [execution_e.id]
    assert execution_d.remaining_dependencies == 1

    assert set(execution_e.parent_task_ids) == {
        execution_c.id,
        execution_d.id,
    }
    assert execution_e.child_task_ids == []
    assert execution_e.remaining_dependencies == 2


def test_start_enqueues_all_root_tasks(
    mock_workflow_start_service,
    task_definition_factory,
    workflow_definition_factory,
    mock_uow,
    mock_execution_queue,
):
    """Starting a workflow should enqueue all tasks without dependencies."""

    task_a = task_definition_factory(key="task_a")
    task_b = task_definition_factory(key="task_b")
    task_c = task_definition_factory(
        key="task_c",
        dependencies=[task_a.id, task_b.id],
    )

    workflow_definition = workflow_definition_factory(
        task_definitions=[
            task_a,
            task_b,
            task_c,
        ]
    )

    mock_uow.workflow_definitions.load.return_value = workflow_definition

    mock_workflow_start_service.start(workflow_definition.id)

    workflow_execution = mock_uow.workflow_executions.create.call_args.args[0]

    executions = {
        task_execution.task_definition_id: task_execution
        for task_execution in workflow_execution.task_executions
    }

    mock_execution_queue.enqueue.assert_called_once()

    enqueued_ids = mock_execution_queue.enqueue.call_args.args[0]

    assert set(enqueued_ids) == {
        executions[task_a.id].id,
        executions[task_b.id].id,
    }


def test_start_snapshots_task_configuration(
    mock_workflow_start_service,
    task_definition_factory,
    workflow_definition_factory,
    mock_uow,
):
    """Task execution configuration should match the source definition."""

    configuration = {
        "url": "https://example.com",
        "options": {
            "timeout": 30,
        },
    }

    task_definition = task_definition_factory(configuration=configuration)
    workflow_definition = workflow_definition_factory(task_definitions=[task_definition])

    mock_uow.workflow_definitions.load.return_value = workflow_definition

    mock_workflow_start_service.start(workflow_definition.id)

    workflow_execution = mock_uow.workflow_executions.create.call_args.args[0]
    task_execution = workflow_execution.task_executions[0]

    assert task_execution.configuration == configuration


def test_start_generates_unique_task_execution_ids(
    mock_workflow_start_service,
    task_definition_factory,
    workflow_definition_factory,
    mock_uow,
):
    """Each task definition should receive a unique task execution identifier."""

    tasks = [
        task_definition_factory(key="task_a"),
        task_definition_factory(key="task_b"),
        task_definition_factory(key="task_c"),
    ]
    workflow_definition = workflow_definition_factory(task_definitions=tasks)

    mock_uow.workflow_definitions.load.return_value = workflow_definition

    mock_workflow_start_service.start(workflow_definition.id)

    workflow_execution = mock_uow.workflow_executions.create.call_args.args[0]

    execution_ids = [task_execution.id for task_execution in workflow_execution.task_executions]

    assert len(execution_ids) == len(set(execution_ids))


def test_start_assigns_tasks_to_workflow_execution(
    mock_workflow_start_service,
    task_definition_factory,
    workflow_definition_factory,
    mock_uow,
):
    """All task executions should belong to the created workflow execution."""

    tasks = [
        task_definition_factory(key="task_a"),
        task_definition_factory(key="task_b"),
        task_definition_factory(key="task_c"),
    ]
    workflow_definition = workflow_definition_factory(task_definitions=tasks)

    mock_uow.workflow_definitions.load.return_value = workflow_definition

    mock_workflow_start_service.start(workflow_definition.id)

    workflow_execution = mock_uow.workflow_executions.create.call_args.args[0]

    assert all(
        task.workflow_execution_id == workflow_execution.id
        for task in workflow_execution.task_executions
    )


# ==================================================================================================
# Existing Unit of Work
# ==================================================================================================


def test_start_and_commit_uses_supplied_unit_of_work(
    mock_workflow_start_service,
    workflow_definition_factory,
    mock_uow,
):
    """Starting with an existing UoW should persist through that UoW."""

    workflow_definition = workflow_definition_factory()
    mock_uow.workflow_definitions.load.return_value = workflow_definition

    workflow_execution_id = mock_workflow_start_service.start_and_commit(
        workflow_definition.id,
        mock_uow,
    )

    mock_uow.workflow_definitions.load.assert_called_once_with(workflow_definition.id)
    mock_uow.workflow_executions.create.assert_called_once()

    workflow_execution = mock_uow.workflow_executions.create.call_args.args[0]

    assert workflow_execution.id == workflow_execution_id
    assert workflow_execution.workflow_definition_id == workflow_definition.id
    assert workflow_execution.status is WorkflowStatus.RUNNING

    mock_uow.commit.assert_called_once_with()


def test_start_and_commit_enqueues_root_tasks(
    mock_workflow_start_service,
    task_definition_factory,
    workflow_definition_factory,
    mock_uow,
    mock_execution_queue,
):
    """Starting with an existing UoW should enqueue roots after committing."""

    task_a = task_definition_factory(key="task_a")
    task_b = task_definition_factory(key="task_b")
    task_c = task_definition_factory(
        key="task_c",
        dependencies=[task_a.id, task_b.id],
    )

    workflow_definition = workflow_definition_factory(
        task_definitions=[
            task_a,
            task_b,
            task_c,
        ]
    )

    mock_uow.workflow_definitions.load.return_value = workflow_definition

    mock_workflow_start_service.start_and_commit(
        workflow_definition.id,
        mock_uow,
    )

    workflow_execution = mock_uow.workflow_executions.create.call_args.args[0]

    executions = {
        task_execution.task_definition_id: task_execution
        for task_execution in workflow_execution.task_executions
    }

    mock_execution_queue.enqueue.assert_called_once()

    enqueued_ids = mock_execution_queue.enqueue.call_args.args[0]

    assert set(enqueued_ids) == {
        executions[task_a.id].id,
        executions[task_b.id].id,
    }


def test_start_and_commit_commits_before_enqueueing(
    mock_workflow_start_service,
    workflow_definition_factory,
    mock_uow,
    mock_execution_queue,
):
    """Existing UoW should commit before runnable tasks are enqueued."""

    workflow_definition = workflow_definition_factory()
    mock_uow.workflow_definitions.load.return_value = workflow_definition

    events = []

    mock_uow.commit.side_effect = lambda: events.append("commit")
    mock_execution_queue.enqueue.side_effect = lambda _: events.append("enqueue")

    mock_workflow_start_service.start_and_commit(
        workflow_definition.id,
        mock_uow,
    )

    assert events == [
        "commit",
        "enqueue",
    ]


def test_start_and_commit_does_not_enqueue_when_commit_fails(
    mock_workflow_start_service,
    workflow_definition_factory,
    mock_uow,
    mock_execution_queue,
):
    """Existing UoW should not enqueue tasks when its commit fails."""

    workflow_definition = workflow_definition_factory()
    mock_uow.workflow_definitions.load.return_value = workflow_definition

    mock_uow.commit.side_effect = RuntimeError("Commit failed.")

    with pytest.raises(RuntimeError, match="Commit failed"):
        mock_workflow_start_service.start_and_commit(
            workflow_definition.id,
            mock_uow,
        )

    mock_uow.workflow_executions.create.assert_called_once()
    mock_execution_queue.enqueue.assert_not_called()


def test_start_and_commit_propagates_queue_failure_after_commit(
    mock_workflow_start_service,
    workflow_definition_factory,
    mock_uow,
    mock_execution_queue,
):
    """Queue failure should propagate after the supplied UoW has committed."""

    workflow_definition = workflow_definition_factory()
    mock_uow.workflow_definitions.load.return_value = workflow_definition
    mock_execution_queue.enqueue.side_effect = RuntimeError("Queue failed.")

    with pytest.raises(RuntimeError, match="Queue failed"):
        mock_workflow_start_service.start_and_commit(
            workflow_definition.id,
            mock_uow,
        )

    mock_uow.workflow_executions.create.assert_called_once()
    mock_uow.commit.assert_called_once_with()


# ==================================================================================================
# Invalid Start
# ==================================================================================================


def test_start_rejects_missing_workflow_definition(
    mock_workflow_start_service,
    mock_uow,
    mock_execution_queue,
):
    """Starting a nonexistent workflow definition should fail without side effects."""

    workflow_definition_id = UUID("12345678-1234-5678-1234-567812345678")

    mock_uow.workflow_definitions.load.return_value = None

    with pytest.raises(
        WorkflowDefinitionNotFoundError,
        match=str(workflow_definition_id),
    ):
        mock_workflow_start_service.start(workflow_definition_id)

    mock_uow.workflow_executions.create.assert_not_called()
    mock_uow.commit.assert_not_called()
    mock_execution_queue.enqueue.assert_not_called()


def test_start_rejects_disabled_workflow_definition(
    mock_workflow_start_service,
    workflow_definition_factory,
    mock_uow,
    mock_execution_queue,
):
    """Starting a disabled workflow definition should fail without side effects."""

    workflow_definition = workflow_definition_factory(enabled=False)

    mock_uow.workflow_definitions.load.return_value = workflow_definition

    with pytest.raises(
        WorkflowDefinitionDisabledError,
        match=str(workflow_definition.id),
    ):
        mock_workflow_start_service.start(workflow_definition.id)

    mock_uow.workflow_executions.create.assert_not_called()
    mock_uow.commit.assert_not_called()
    mock_execution_queue.enqueue.assert_not_called()


def test_start_and_commit_rejects_missing_workflow_definition(
    mock_workflow_start_service,
    mock_uow,
    mock_execution_queue,
):
    """Existing UoW should reject a nonexistent workflow without side effects."""

    workflow_definition_id = UUID("12345678-1234-5678-1234-567812345678")

    mock_uow.workflow_definitions.load.return_value = None

    with pytest.raises(
        WorkflowDefinitionNotFoundError,
        match=str(workflow_definition_id),
    ):
        mock_workflow_start_service.start_and_commit(
            workflow_definition_id,
            mock_uow,
        )

    mock_uow.workflow_executions.create.assert_not_called()
    mock_uow.commit.assert_not_called()
    mock_execution_queue.enqueue.assert_not_called()


def test_start_and_commit_rejects_disabled_workflow_definition(
    mock_workflow_start_service,
    workflow_definition_factory,
    mock_uow,
    mock_execution_queue,
):
    """Existing UoW should reject a disabled workflow without side effects."""

    workflow_definition = workflow_definition_factory(enabled=False)

    mock_uow.workflow_definitions.load.return_value = workflow_definition

    with pytest.raises(
        WorkflowDefinitionDisabledError,
        match=str(workflow_definition.id),
    ):
        mock_workflow_start_service.start_and_commit(
            workflow_definition.id,
            mock_uow,
        )

    mock_uow.workflow_executions.create.assert_not_called()
    mock_uow.commit.assert_not_called()
    mock_execution_queue.enqueue.assert_not_called()


# ==================================================================================================
# Persistence and Queue Boundaries
# ==================================================================================================


def test_start_does_not_enqueue_when_commit_fails(
    mock_workflow_start_service,
    workflow_definition_factory,
    mock_uow,
    mock_execution_queue,
):
    """Tasks should not be enqueued if execution persistence fails."""

    workflow_definition = workflow_definition_factory()
    mock_uow.workflow_definitions.load.return_value = workflow_definition

    mock_uow.commit.side_effect = RuntimeError("Commit failed.")

    with pytest.raises(RuntimeError, match="Commit failed"):
        mock_workflow_start_service.start(workflow_definition.id)

    mock_uow.workflow_executions.create.assert_called_once()
    mock_execution_queue.enqueue.assert_not_called()


def test_start_commits_before_enqueueing(
    mock_workflow_start_service,
    workflow_definition_factory,
    mock_uow,
    mock_execution_queue,
):
    """Execution persistence should commit before runnable tasks are enqueued."""

    workflow_definition = workflow_definition_factory()
    mock_uow.workflow_definitions.load.return_value = workflow_definition

    events = []

    mock_uow.commit.side_effect = lambda: events.append("commit")
    mock_execution_queue.enqueue.side_effect = lambda _: events.append("enqueue")

    mock_workflow_start_service.start(workflow_definition.id)

    assert events == [
        "commit",
        "enqueue",
    ]


def test_start_propagates_queue_failure_after_commit(
    mock_workflow_start_service,
    workflow_definition_factory,
    mock_uow,
    mock_execution_queue,
):
    """A queue failure should occur only after the execution has been committed."""

    workflow_definition = workflow_definition_factory()
    mock_uow.workflow_definitions.load.return_value = workflow_definition
    mock_execution_queue.enqueue.side_effect = RuntimeError("Queue failed.")

    with pytest.raises(RuntimeError, match="Queue failed"):
        mock_workflow_start_service.start(workflow_definition.id)

    mock_uow.workflow_executions.create.assert_called_once()
    mock_uow.commit.assert_called_once_with()
