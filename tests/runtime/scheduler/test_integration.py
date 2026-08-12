"""End-to-end tests for chronological trigger scheduling."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from threading import Barrier, Thread
from time import monotonic, sleep
from uuid import uuid4

from sqlalchemy import func, select

from automation_platform.domain import TaskStatus, WorkflowStatus
from automation_platform.persistence.workflow_definitions.model import (
    TriggerDefinitionModel,
)
from automation_platform.persistence.workflow_executions.model import (
    WorkflowExecutionModel,
)
from automation_platform.runtime.worker import Worker
from tests.helpers import (
    get_task,
    load_chronological_trigger_state,
    wait_for_terminal_workflow,
)

# ==================================================================================================
# Scheduling Pipeline
# ==================================================================================================


def test_scheduler_processes_due_trigger_through_complete_workflow(
    workflow_definition_service,
    create_workflow_definition_factory,
    create_task_definition_factory,
    create_trigger_definition_factory,
    session_factory,
    uow_factory,
    scheduler,
    postgres_queue,
    task_processing_service,
):
    """A due trigger should schedule and execute its workflow end to end."""

    occurrence = datetime.now(timezone.utc) + timedelta(milliseconds=100)

    definition_id = workflow_definition_service.create(
        create_workflow_definition_factory(
            name="Scheduled workflow",
            description="Workflow started by a chronological trigger.",
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

    trigger_definition = _load_trigger_definition(
        session_factory,
        definition_id,
    )

    state = load_chronological_trigger_state(
        session_factory,
        trigger_definition.id,
    )

    assert state is not None
    assert state.next_run_at == occurrence

    worker = Worker(
        worker_id=uuid4(),
        queue=postgres_queue,
        task_processing_service=task_processing_service,
        poll_interval=timedelta(milliseconds=10),
        heartbeat_interval=timedelta(milliseconds=50),
    )

    scheduler_thread = Thread(
        target=scheduler.run,
        name="test-scheduler",
    )
    worker_thread = Thread(
        target=worker.run,
        name="test-scheduler-worker",
    )

    scheduler_thread.start()
    worker_thread.start()

    try:
        workflow_execution_id = _wait_for_workflow_execution_id(
            session_factory,
            definition_id,
        )

        execution = wait_for_terminal_workflow(
            uow_factory,
            workflow_execution_id,
        )
    finally:
        scheduler.stop()
        worker.stop()

        scheduler_thread.join(timeout=2)
        worker_thread.join(timeout=2)

    assert not scheduler_thread.is_alive()
    assert not worker_thread.is_alive()

    assert execution.status is WorkflowStatus.COMPLETED

    task = get_task(execution, "task")

    assert task.status is TaskStatus.COMPLETED
    assert task.output.values == {
        "result": "success",
    }

    state = load_chronological_trigger_state(
        session_factory,
        trigger_definition.id,
    )

    assert state is None

    assert (
        _count_workflow_executions(
            session_factory,
            definition_id,
        )
        == 1
    )


def test_scheduler_advances_recurring_trigger_after_occurrence(
    workflow_definition_service,
    create_workflow_definition_factory,
    create_task_definition_factory,
    create_trigger_definition_factory,
    session_factory,
    scheduler,
):
    """A recurring trigger should advance its durable schedule after firing."""

    definition_id = workflow_definition_service.create(
        create_workflow_definition_factory(
            name="Recurring workflow",
            description="Workflow started by an interval trigger.",
            tasks=[
                create_task_definition_factory(
                    key="task",
                    plugin_type="successful",
                )
            ],
            triggers=[
                create_trigger_definition_factory(
                    plugin_type="interval",
                    configuration={
                        "interval_seconds": 60,
                    },
                )
            ],
        )
    )

    trigger_definition = _load_trigger_definition(
        session_factory,
        definition_id,
    )

    due_at = datetime.now(timezone.utc) - timedelta(seconds=1)

    _set_next_run_at(
        session_factory,
        trigger_definition.id,
        due_at,
    )

    scheduler_thread = Thread(
        target=scheduler.run,
        name="test-recurring-scheduler",
    )

    scheduler_thread.start()

    try:
        _wait_until(
            lambda: _schedule_has_advanced(
                session_factory,
                trigger_definition.id,
                due_at,
            )
        )
    finally:
        scheduler.stop()
        scheduler_thread.join(timeout=2)

    assert not scheduler_thread.is_alive()

    state = load_chronological_trigger_state(
        session_factory,
        trigger_definition.id,
    )

    assert state is not None
    assert state.next_run_at == due_at + timedelta(seconds=60)

    assert (
        _count_workflow_executions(
            session_factory,
            definition_id,
        )
        == 1
    )


def test_scheduler_does_not_process_disabled_trigger(
    workflow_definition_service,
    create_workflow_definition_factory,
    create_task_definition_factory,
    create_trigger_definition_factory,
    session_factory,
    scheduler,
    postgres_queue,
):
    """A disabled due trigger should remain scheduled without starting work."""

    definition_id = workflow_definition_service.create(
        create_workflow_definition_factory(
            name="Disabled scheduled workflow",
            description="Disabled trigger should not start its workflow.",
            tasks=[
                create_task_definition_factory(
                    key="task",
                    plugin_type="successful",
                )
            ],
            triggers=[
                create_trigger_definition_factory(
                    plugin_type="interval",
                    configuration={
                        "interval_seconds": 60,
                    },
                    enabled=False,
                )
            ],
        )
    )

    trigger_definition = _load_trigger_definition(
        session_factory,
        definition_id,
    )

    due_at = datetime.now(timezone.utc) - timedelta(minutes=1)

    _set_next_run_at(
        session_factory,
        trigger_definition.id,
        due_at,
    )

    scheduler_thread = Thread(
        target=scheduler.run,
        name="test-disabled-scheduler",
    )

    scheduler_thread.start()

    try:
        # Give the Scheduler several opportunities to observe the due trigger.
        sleep(0.05)
    finally:
        scheduler.stop()
        scheduler_thread.join(timeout=2)

    assert not scheduler_thread.is_alive()

    state = load_chronological_trigger_state(
        session_factory,
        trigger_definition.id,
    )

    assert state is not None
    assert state.next_run_at == due_at

    assert (
        _count_workflow_executions(
            session_factory,
            definition_id,
        )
        == 0
    )

    claim = postgres_queue.claim(uuid4())

    assert claim is None


# ==================================================================================================
# Concurrent Scheduling
# ==================================================================================================


def test_concurrent_processing_processes_single_due_trigger_once(
    workflow_definition_service,
    create_workflow_definition_factory,
    create_task_definition_factory,
    create_trigger_definition_factory,
    session_factory,
    chronological_trigger_service_factory,
):
    """Concurrent schedulers should process one due occurrence exactly once."""

    definition_id = workflow_definition_service.create(
        create_workflow_definition_factory(
            name="Concurrent single trigger",
            description="One due occurrence processed by concurrent schedulers.",
            tasks=[
                create_task_definition_factory(
                    key="task",
                    plugin_type="successful",
                )
            ],
            triggers=[
                create_trigger_definition_factory(
                    plugin_type="interval",
                    configuration={
                        "interval_seconds": 60,
                    },
                )
            ],
        )
    )

    trigger_definition = _load_trigger_definition(
        session_factory,
        definition_id,
    )

    due_at = datetime.now(timezone.utc) - timedelta(seconds=1)

    _set_next_run_at(
        session_factory,
        trigger_definition.id,
        due_at,
    )

    barrier = Barrier(2)

    def process():
        service = chronological_trigger_service_factory()

        barrier.wait()

        return service.process_next_due()

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(process),
            executor.submit(process),
        ]

        results = [future.result(timeout=2) for future in futures]

    assert sorted(results) == [False, True]

    state = load_chronological_trigger_state(
        session_factory,
        trigger_definition.id,
    )

    assert state is not None
    assert state.next_run_at == due_at + timedelta(seconds=60)

    assert (
        _count_workflow_executions(
            session_factory,
            definition_id,
        )
        == 1
    )


def test_concurrent_processing_processes_different_due_triggers(
    workflow_definition_service,
    create_workflow_definition_factory,
    create_task_definition_factory,
    create_trigger_definition_factory,
    session_factory,
    chronological_trigger_service_factory,
):
    """Concurrent schedulers should independently process different due triggers."""

    first_definition_id = workflow_definition_service.create(
        create_workflow_definition_factory(
            name="Concurrent trigger A",
            description="First concurrently scheduled workflow.",
            tasks=[
                create_task_definition_factory(
                    key="task",
                    plugin_type="successful",
                )
            ],
            triggers=[
                create_trigger_definition_factory(
                    plugin_type="interval",
                    configuration={
                        "interval_seconds": 60,
                    },
                )
            ],
        )
    )

    second_definition_id = workflow_definition_service.create(
        create_workflow_definition_factory(
            name="Concurrent trigger B",
            description="Second concurrently scheduled workflow.",
            tasks=[
                create_task_definition_factory(
                    key="task",
                    plugin_type="successful",
                )
            ],
            triggers=[
                create_trigger_definition_factory(
                    plugin_type="interval",
                    configuration={
                        "interval_seconds": 60,
                    },
                )
            ],
        )
    )

    first_trigger = _load_trigger_definition(
        session_factory,
        first_definition_id,
    )
    second_trigger = _load_trigger_definition(
        session_factory,
        second_definition_id,
    )

    first_due_at = datetime.now(timezone.utc) - timedelta(seconds=2)
    second_due_at = datetime.now(timezone.utc) - timedelta(seconds=1)

    _set_next_run_at(
        session_factory,
        first_trigger.id,
        first_due_at,
    )
    _set_next_run_at(
        session_factory,
        second_trigger.id,
        second_due_at,
    )

    barrier = Barrier(2)

    def process():
        service = chronological_trigger_service_factory()

        barrier.wait()

        return service.process_next_due()

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(process),
            executor.submit(process),
        ]

        results = [future.result(timeout=2) for future in futures]

    assert results == [True, True]

    first_state = load_chronological_trigger_state(
        session_factory,
        first_trigger.id,
    )
    second_state = load_chronological_trigger_state(
        session_factory,
        second_trigger.id,
    )

    assert first_state is not None
    assert second_state is not None

    assert first_state.next_run_at == (first_due_at + timedelta(seconds=60))
    assert second_state.next_run_at == (second_due_at + timedelta(seconds=60))

    assert (
        _count_workflow_executions(
            session_factory,
            first_definition_id,
        )
        == 1
    )

    assert (
        _count_workflow_executions(
            session_factory,
            second_definition_id,
        )
        == 1
    )


# ==================================================================================================
# Helpers
# ==================================================================================================


def _load_trigger_definition(
    session_factory,
    workflow_definition_id,
):
    """Load the first persisted trigger definition for a workflow."""

    with session_factory() as session:
        statement = (
            select(TriggerDefinitionModel)
            .where(TriggerDefinitionModel.workflow_definition_id == workflow_definition_id)
            .order_by(TriggerDefinitionModel.id)
            .limit(1)
        )

        trigger_definition = session.scalars(statement).first()

        if trigger_definition is None:
            raise AssertionError(
                f"Workflow definition {workflow_definition_id} "
                "does not contain a persisted trigger definition."
            )

        session.expunge(trigger_definition)

        return trigger_definition


def _set_next_run_at(
    session_factory,
    trigger_definition_id,
    next_run_at,
) -> None:
    """Set chronological trigger state directly for integration setup."""

    from automation_platform.persistence.chronological_triggers.model import (
        ChronologicalTriggerStateModel,
    )

    with session_factory() as session:
        state = session.get(
            ChronologicalTriggerStateModel,
            trigger_definition_id,
        )

        if state is None:
            raise AssertionError(
                f"Chronological trigger state {trigger_definition_id} does not exist."
            )

        state.next_run_at = next_run_at
        session.commit()


def _schedule_has_advanced(
    session_factory,
    trigger_definition_id,
    previous_next_run_at,
) -> bool:
    """Return whether a trigger's next occurrence has advanced."""

    state = load_chronological_trigger_state(
        session_factory,
        trigger_definition_id,
    )

    return state is not None and state.next_run_at > previous_next_run_at


def _wait_for_workflow_execution_id(
    session_factory,
    workflow_definition_id,
    timeout: float = 2.0,
):
    """Wait for a scheduled workflow execution to be persisted."""

    workflow_execution_id = None

    def execution_exists() -> bool:
        nonlocal workflow_execution_id

        with session_factory() as session:
            statement = (
                select(WorkflowExecutionModel.id)
                .where(WorkflowExecutionModel.workflow_definition_id == workflow_definition_id)
                .limit(1)
            )

            workflow_execution_id = session.scalar(statement)

        return workflow_execution_id is not None

    _wait_until(
        execution_exists,
        timeout=timeout,
    )

    return workflow_execution_id


def _count_workflow_executions(
    session_factory,
    workflow_definition_id,
) -> int:
    """Count persisted executions belonging to a workflow definition."""

    with session_factory() as session:
        statement = (
            select(func.count())
            .select_from(WorkflowExecutionModel)
            .where(WorkflowExecutionModel.workflow_definition_id == workflow_definition_id)
        )

        return session.scalar(statement) or 0


def _wait_until(
    condition,
    timeout: float = 2.0,
) -> None:
    """Wait until a condition becomes true."""

    deadline = monotonic() + timeout

    while monotonic() < deadline:
        if condition():
            return

        sleep(0.001)

    raise AssertionError(f"Condition was not met within {timeout} seconds.")
