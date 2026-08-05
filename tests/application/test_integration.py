"""Integration tests for application workflow execution."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy import select

from automation_platform.domain import TaskStatus, WorkflowStatus
from automation_platform.persistence.chronological_triggers._model import (
    ChronologicalTriggerStateModel,
)
from automation_platform.persistence.workflow_definitions._model import (
    WorkflowDefinitionModel,
)
from tests.helpers import get_task, load_execution

# ==================================================================================================
# Helpers
# ==================================================================================================


def load_chronological_trigger_state(
    uow_factory,
    trigger_definition_id,
):
    """Load persisted chronological scheduling state."""

    with uow_factory() as uow:
        return uow._session.get(
            ChronologicalTriggerStateModel,
            trigger_definition_id,
        )


# ==================================================================================================
# Workflow Start
# ==================================================================================================


def test_start_workflow_creates_execution_with_root_tasks(
    workflow_definition_service,
    workflow_start_service,
    create_workflow_definition_factory,
    create_task_definition_factory,
    uow_factory,
):
    """Starting a workflow should persist its execution graph."""

    definition_id = workflow_definition_service.create(
        create_workflow_definition_factory(
            tasks=[
                create_task_definition_factory(
                    key="root",
                    plugin_type="successful",
                ),
                create_task_definition_factory(
                    key="child",
                    plugin_type="successful",
                    dependencies=["root"],
                ),
            ],
            triggers=[],
        )
    )

    workflow_execution_id = workflow_start_service.start(definition_id)

    execution = load_execution(
        uow_factory,
        workflow_execution_id,
    )

    assert execution is not None
    assert execution.workflow_definition_id == definition_id
    assert execution.status == WorkflowStatus.RUNNING

    root = get_task(execution, "root")
    child = get_task(execution, "child")

    assert root.status == TaskStatus.PENDING
    assert root.remaining_dependencies == 0

    assert child.status == TaskStatus.PENDING
    assert child.remaining_dependencies == 1

    assert root.id in child.parent_task_ids
    assert child.id in root.child_task_ids


# ==================================================================================================
# Chronological Trigger Initialization
# ==================================================================================================


def test_creating_interval_trigger_initializes_chronological_state(
    workflow_definition_service,
    create_workflow_definition_factory,
    create_task_definition_factory,
    create_trigger_definition_factory,
    uow_factory,
):
    """Creating an interval trigger should initialize its scheduling state."""

    before_creation = datetime.now(timezone.utc)

    definition_id = workflow_definition_service.create(
        create_workflow_definition_factory(
            tasks=[
                create_task_definition_factory(
                    key="task",
                    plugin_type="successful",
                )
            ],
            triggers=[
                create_trigger_definition_factory(
                    plugin_type="interval",
                    configuration={"interval_seconds": 60},
                )
            ],
        )
    )

    after_creation = datetime.now(timezone.utc)

    with uow_factory() as uow:
        workflow_definition = uow.workflow_definitions.load(definition_id)

    assert workflow_definition is not None

    trigger_definition = workflow_definition.trigger_definitions[0]

    state = load_chronological_trigger_state(
        uow_factory,
        trigger_definition.id,
    )

    assert state is not None
    assert state.trigger_definition_id == trigger_definition.id
    assert (
        before_creation + timedelta(seconds=60)
        <= state.next_run_at
        <= after_creation + timedelta(seconds=60)
    )


def test_trigger_initialization_failure_rolls_back_workflow_definition(
    workflow_definition_service,
    create_workflow_definition_factory,
    create_task_definition_factory,
    create_trigger_definition_factory,
    session,
):
    """Trigger initialization failure should roll back the complete definition."""

    workflow_name = "Initialization rollback workflow"

    request = create_workflow_definition_factory(
        name=workflow_name,
        tasks=[
            create_task_definition_factory(
                key="task",
                plugin_type="successful",
            )
        ],
        triggers=[
            create_trigger_definition_factory(
                plugin_type="failing_initialization",
                configuration={},
            )
        ],
    )

    with pytest.raises(
        RuntimeError,
        match="Trigger initialization failed",
    ):
        workflow_definition_service.create(request)

    workflow_definition = session.scalar(
        select(WorkflowDefinitionModel).where(WorkflowDefinitionModel.name == workflow_name)
    )

    assert workflow_definition is None

    chronological_state = session.scalar(select(ChronologicalTriggerStateModel))

    assert chronological_state is None


# ==================================================================================================
# Chronological Trigger Processing
# ==================================================================================================


def test_processing_due_trigger_starts_workflow_and_advances_schedule(
    workflow_definition_service,
    chronological_trigger_service,
    create_workflow_definition_factory,
    create_task_definition_factory,
    create_trigger_definition_factory,
    uow_factory,
    postgres_queue,
):
    """Processing a due trigger should advance it and start its workflow."""

    definition_id = workflow_definition_service.create(
        create_workflow_definition_factory(
            tasks=[
                create_task_definition_factory(
                    key="task",
                    plugin_type="successful",
                )
            ],
            triggers=[
                create_trigger_definition_factory(
                    plugin_type="interval",
                    configuration={"interval_seconds": 60},
                )
            ],
        )
    )

    with uow_factory() as uow:
        workflow_definition = uow.workflow_definitions.load(definition_id)

        assert workflow_definition is not None

        trigger_definition = workflow_definition.trigger_definitions[0]
        due_at = datetime.now(timezone.utc) - timedelta(seconds=30)

        uow.chronological_triggers.update_next_run(
            trigger_definition.id,
            due_at,
        )
        uow.commit()

    processed = chronological_trigger_service.process_next_due()

    assert processed is True

    state = load_chronological_trigger_state(
        uow_factory,
        trigger_definition.id,
    )

    assert state is not None
    assert state.next_run_at == due_at + timedelta(seconds=60)

    claim = postgres_queue.claim(uuid4())

    assert claim is not None


def test_processing_with_no_due_trigger_returns_false(
    workflow_definition_service,
    chronological_trigger_service,
    create_workflow_definition_factory,
    create_task_definition_factory,
    create_trigger_definition_factory,
):
    """Processing should return false when no chronological trigger is due."""

    workflow_definition_service.create(
        create_workflow_definition_factory(
            tasks=[
                create_task_definition_factory(
                    key="task",
                    plugin_type="successful",
                )
            ],
            triggers=[
                create_trigger_definition_factory(
                    plugin_type="interval",
                    configuration={"interval_seconds": 3600},
                )
            ],
        )
    )

    processed = chronological_trigger_service.process_next_due()

    assert processed is False


def test_overdue_interval_trigger_advances_from_scheduled_occurrence(
    workflow_definition_service,
    chronological_trigger_service,
    create_workflow_definition_factory,
    create_task_definition_factory,
    create_trigger_definition_factory,
    uow_factory,
):
    """An overdue interval trigger should advance one scheduled occurrence."""

    definition_id = workflow_definition_service.create(
        create_workflow_definition_factory(
            tasks=[
                create_task_definition_factory(
                    key="task",
                    plugin_type="successful",
                )
            ],
            triggers=[
                create_trigger_definition_factory(
                    plugin_type="interval",
                    configuration={"interval_seconds": 3600},
                )
            ],
        )
    )

    with uow_factory() as uow:
        workflow_definition = uow.workflow_definitions.load(definition_id)

        assert workflow_definition is not None

        trigger_definition = workflow_definition.trigger_definitions[0]

        scheduled_at = datetime.now(timezone.utc) - timedelta(
            hours=2,
            minutes=30,
        )

        uow.chronological_triggers.update_next_run(
            trigger_definition.id,
            scheduled_at,
        )
        uow.commit()

    processed = chronological_trigger_service.process_next_due()

    assert processed is True

    state = load_chronological_trigger_state(
        uow_factory,
        trigger_definition.id,
    )

    assert state is not None
    assert state.next_run_at == scheduled_at + timedelta(hours=1)


def test_processing_terminal_trigger_deletes_scheduling_state(
    workflow_definition_service,
    chronological_trigger_service,
    create_workflow_definition_factory,
    create_task_definition_factory,
    create_trigger_definition_factory,
    uow_factory,
    postgres_queue,
):
    """Processing a terminal trigger should delete its state and start its workflow."""

    occurrence = datetime.now(timezone.utc) - timedelta(seconds=1)

    definition_id = workflow_definition_service.create(
        create_workflow_definition_factory(
            tasks=[
                create_task_definition_factory(
                    key="task",
                    plugin_type="successful",
                )
            ],
            triggers=[
                create_trigger_definition_factory(
                    plugin_type="one_shot",
                    configuration={
                        "occurrence": occurrence.isoformat(),
                    },
                )
            ],
        )
    )

    with uow_factory() as uow:
        workflow_definition = uow.workflow_definitions.load(definition_id)

    assert workflow_definition is not None

    trigger_definition = workflow_definition.trigger_definitions[0]

    state = load_chronological_trigger_state(
        uow_factory,
        trigger_definition.id,
    )

    assert state is not None
    assert state.next_run_at == occurrence

    processed = chronological_trigger_service.process_next_due()

    assert processed is True

    state = load_chronological_trigger_state(
        uow_factory,
        trigger_definition.id,
    )

    assert state is None

    claim = postgres_queue.claim(uuid4())

    assert claim is not None


def test_disabled_due_trigger_is_not_processed(
    workflow_definition_service,
    chronological_trigger_service,
    create_workflow_definition_factory,
    create_task_definition_factory,
    create_trigger_definition_factory,
    uow_factory,
    postgres_queue,
):
    """A disabled chronological trigger should not start its workflow."""

    definition_id = workflow_definition_service.create(
        create_workflow_definition_factory(
            tasks=[
                create_task_definition_factory(
                    key="task",
                    plugin_type="successful",
                )
            ],
            triggers=[
                create_trigger_definition_factory(
                    plugin_type="interval",
                    configuration={"interval_seconds": 60},
                    enabled=False,
                )
            ],
        )
    )

    with uow_factory() as uow:
        workflow_definition = uow.workflow_definitions.load(definition_id)

        assert workflow_definition is not None

        trigger_definition = workflow_definition.trigger_definitions[0]

        due_at = datetime.now(timezone.utc) - timedelta(minutes=1)

        uow.chronological_triggers.update_next_run(
            trigger_definition.id,
            due_at,
        )
        uow.commit()

    processed = chronological_trigger_service.process_next_due()

    assert processed is False

    state = load_chronological_trigger_state(
        uow_factory,
        trigger_definition.id,
    )

    assert state is not None
    assert state.next_run_at == due_at

    assert postgres_queue.claim(uuid4()) is None


# ==================================================================================================
# Successful Processing
# ==================================================================================================


def test_processing_root_makes_child_runnable(
    workflow_definition_service,
    workflow_start_service,
    task_processing_service,
    create_workflow_definition_factory,
    create_task_definition_factory,
    uow_factory,
):
    """Completing a root task should make its dependent task runnable."""

    definition_id = workflow_definition_service.create(
        create_workflow_definition_factory(
            tasks=[
                create_task_definition_factory(
                    key="root",
                    plugin_type="successful",
                ),
                create_task_definition_factory(
                    key="child",
                    plugin_type="successful",
                    dependencies=["root"],
                ),
            ],
            triggers=[],
        )
    )

    workflow_execution_id = workflow_start_service.start(definition_id)

    execution = load_execution(
        uow_factory,
        workflow_execution_id,
    )

    root = get_task(
        execution,
        "root",
    )

    result = task_processing_service.process(root.id)

    execution = load_execution(
        uow_factory,
        workflow_execution_id,
    )

    root = get_task(
        execution,
        "root",
    )
    child = get_task(
        execution,
        "child",
    )

    assert root.status == TaskStatus.COMPLETED
    assert root.output.values == {
        "result": "success",
    }

    assert child.status == TaskStatus.PENDING
    assert child.remaining_dependencies == 0

    assert result.enqueue_task_ids == [
        child.id,
    ]
    assert result.should_retry is False


def test_parent_output_is_passed_to_child(
    workflow_definition_service,
    workflow_start_service,
    task_processing_service,
    create_workflow_definition_factory,
    create_task_definition_factory,
    uow_factory,
):
    """Child plugins should receive persisted outputs from their parents."""

    definition_id = workflow_definition_service.create(
        create_workflow_definition_factory(
            tasks=[
                create_task_definition_factory(
                    key="parent",
                    plugin_type="successful",
                ),
                create_task_definition_factory(
                    key="child",
                    plugin_type="input",
                    dependencies=["parent"],
                ),
            ],
            triggers=[],
        )
    )

    workflow_execution_id = workflow_start_service.start(definition_id)

    execution = load_execution(
        uow_factory,
        workflow_execution_id,
    )

    parent = get_task(
        execution,
        "parent",
    )

    parent_result = task_processing_service.process(parent.id)

    assert len(parent_result.enqueue_task_ids) == 1

    child_id = parent_result.enqueue_task_ids[0]

    task_processing_service.process(child_id)

    execution = load_execution(
        uow_factory,
        workflow_execution_id,
    )

    child = get_task(
        execution,
        "child",
    )

    assert child.status == TaskStatus.COMPLETED
    assert child.output.values == {
        "inputs": {
            "parent": {
                "result": "success",
            }
        }
    }


def test_processing_all_tasks_completes_workflow(
    workflow_definition_service,
    workflow_start_service,
    task_processing_service,
    create_workflow_definition_factory,
    create_task_definition_factory,
    uow_factory,
):
    """Completing every task should complete the workflow."""

    definition_id = workflow_definition_service.create(
        create_workflow_definition_factory(
            tasks=[
                create_task_definition_factory(
                    key="task_a",
                    plugin_type="successful",
                ),
                create_task_definition_factory(
                    key="task_b",
                    plugin_type="successful",
                    dependencies=["task_a"],
                ),
                create_task_definition_factory(
                    key="task_c",
                    plugin_type="successful",
                    dependencies=["task_b"],
                ),
            ],
            triggers=[],
        )
    )

    workflow_execution_id = workflow_start_service.start(definition_id)

    execution = load_execution(
        uow_factory,
        workflow_execution_id,
    )

    task_a = get_task(
        execution,
        "task_a",
    )

    result = task_processing_service.process(task_a.id)

    assert len(result.enqueue_task_ids) == 1

    result = task_processing_service.process(result.enqueue_task_ids[0])

    assert len(result.enqueue_task_ids) == 1

    result = task_processing_service.process(result.enqueue_task_ids[0])

    assert result.enqueue_task_ids == []
    assert result.should_retry is False

    execution = load_execution(
        uow_factory,
        workflow_execution_id,
    )

    assert execution.status == WorkflowStatus.COMPLETED
    assert execution.completed_at is not None

    assert all(task.status == TaskStatus.COMPLETED for task in execution.task_executions)


# ==================================================================================================
# Retries
# ==================================================================================================


def test_failed_task_retries_then_succeeds(
    workflow_definition_service,
    workflow_start_service,
    task_processing_service,
    create_workflow_definition_factory,
    create_task_definition_factory,
    uow_factory,
):
    """A retryable failure should remain running and later complete."""

    definition_id = workflow_definition_service.create(
        create_workflow_definition_factory(
            tasks=[
                create_task_definition_factory(
                    key="task",
                    plugin_type="fail_once",
                    max_tries=2,
                )
            ],
            triggers=[],
        )
    )

    workflow_execution_id = workflow_start_service.start(definition_id)

    execution = load_execution(
        uow_factory,
        workflow_execution_id,
    )

    task = get_task(
        execution,
        "task",
    )

    first_result = task_processing_service.process(task.id)

    assert first_result.enqueue_task_ids == []
    assert first_result.should_retry is True

    execution = load_execution(
        uow_factory,
        workflow_execution_id,
    )

    task = get_task(
        execution,
        "task",
    )

    assert task.status == TaskStatus.RUNNING
    assert execution.status == WorkflowStatus.RUNNING

    second_result = task_processing_service.process(task.id)

    assert second_result.enqueue_task_ids == []
    assert second_result.should_retry is False

    execution = load_execution(
        uow_factory,
        workflow_execution_id,
    )

    task = get_task(
        execution,
        "task",
    )

    assert task.status == TaskStatus.COMPLETED
    assert execution.status == WorkflowStatus.COMPLETED


# ==================================================================================================
# Terminal Failure
# ==================================================================================================


def test_terminal_failure_fails_workflow_and_cancels_remaining_tasks(
    workflow_definition_service,
    workflow_start_service,
    task_processing_service,
    create_workflow_definition_factory,
    create_task_definition_factory,
    uow_factory,
):
    """Exhausting a task's tries should fail its workflow and cancel remaining work."""

    definition_id = workflow_definition_service.create(
        create_workflow_definition_factory(
            tasks=[
                create_task_definition_factory(
                    key="failing",
                    plugin_type="failing",
                    max_tries=1,
                ),
                create_task_definition_factory(
                    key="sibling",
                    plugin_type="successful",
                ),
                create_task_definition_factory(
                    key="child",
                    plugin_type="successful",
                    dependencies=["failing"],
                ),
            ],
            triggers=[],
        )
    )

    workflow_execution_id = workflow_start_service.start(definition_id)

    execution = load_execution(
        uow_factory,
        workflow_execution_id,
    )

    failing = get_task(
        execution,
        "failing",
    )

    result = task_processing_service.process(failing.id)

    assert result.enqueue_task_ids == []
    assert result.should_retry is False

    execution = load_execution(
        uow_factory,
        workflow_execution_id,
    )

    failing = get_task(
        execution,
        "failing",
    )
    sibling = get_task(
        execution,
        "sibling",
    )
    child = get_task(
        execution,
        "child",
    )

    assert execution.status == WorkflowStatus.FAILED
    assert execution.completed_at is not None

    assert failing.status == TaskStatus.FAILED

    assert sibling.status == TaskStatus.CANCELLED
    assert sibling.completed_at is not None

    assert child.status == TaskStatus.CANCELLED
    assert child.completed_at is not None


# ==================================================================================================
# Dependency Graph
# ==================================================================================================


def test_join_task_waits_for_all_parent_tasks(
    workflow_definition_service,
    workflow_start_service,
    task_processing_service,
    create_workflow_definition_factory,
    create_task_definition_factory,
    uow_factory,
):
    """A task with multiple parents should run only after every parent completes."""

    definition_id = workflow_definition_service.create(
        create_workflow_definition_factory(
            tasks=[
                create_task_definition_factory(
                    key="root",
                    plugin_type="successful",
                ),
                create_task_definition_factory(
                    key="left",
                    plugin_type="successful",
                    dependencies=["root"],
                ),
                create_task_definition_factory(
                    key="right",
                    plugin_type="successful",
                    dependencies=["root"],
                ),
                create_task_definition_factory(
                    key="join",
                    plugin_type="successful",
                    dependencies=["left", "right"],
                ),
            ],
            triggers=[],
        )
    )

    workflow_execution_id = workflow_start_service.start(definition_id)

    execution = load_execution(
        uow_factory,
        workflow_execution_id,
    )

    root = get_task(
        execution,
        "root",
    )

    root_result = task_processing_service.process(root.id)

    assert len(root_result.enqueue_task_ids) == 2

    execution = load_execution(
        uow_factory,
        workflow_execution_id,
    )

    left = get_task(
        execution,
        "left",
    )
    right = get_task(
        execution,
        "right",
    )
    join = get_task(
        execution,
        "join",
    )

    assert set(root_result.enqueue_task_ids) == {
        left.id,
        right.id,
    }

    first_result = task_processing_service.process(left.id)

    assert join.id not in first_result.enqueue_task_ids

    execution = load_execution(
        uow_factory,
        workflow_execution_id,
    )

    join = get_task(
        execution,
        "join",
    )

    assert join.remaining_dependencies == 1

    second_result = task_processing_service.process(right.id)

    assert second_result.enqueue_task_ids == [
        join.id,
    ]

    execution = load_execution(
        uow_factory,
        workflow_execution_id,
    )

    join = get_task(
        execution,
        "join",
    )

    assert join.remaining_dependencies == 0
