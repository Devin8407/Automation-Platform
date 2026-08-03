"""End-to-end tests for Worker workflow execution."""

from __future__ import annotations

from datetime import timedelta
from threading import Thread
from time import monotonic, sleep
from uuid import uuid4

from automation_platform.application.task_processing import TaskProcessingService
from automation_platform.application.workflow_definitions import (
    CreateTaskDefinition,
    CreateWorkflowDefinition,
    WorkflowDefinitionService,
)
from automation_platform.application.workflow_start import WorkflowStartService
from automation_platform.domain import TaskStatus, WorkflowStatus
from automation_platform.execution_queue.postgres import PostgresExecutionQueue
from automation_platform.plugins import TaskRegistry, TriggerRegistry
from automation_platform.runtime.worker import Worker

# ==================================================================================================
# Helpers
# ==================================================================================================


def load_execution(uow_factory, workflow_execution_id):
    """Load a workflow execution using real persistence."""

    with uow_factory() as uow:
        return uow.workflow_executions.load(workflow_execution_id)


def get_task(execution, key):
    """Return a task execution by key."""

    return next(task for task in execution.task_executions if task.key == key)


# ==================================================================================================
# DAG Happy Path
# ==================================================================================================


def test_worker_executes_diamond_workflow_to_completion(
    uow_factory,
    session_factory,
):
    r"""
    Execute:

             produce
              /   \
         collect-a collect-b
              \   /
              collect

    through the real PostgreSQL queue and Worker.
    """

    task_registry = TaskRegistry()
    trigger_registry = TriggerRegistry()

    queue = PostgresExecutionQueue(
        session_factory=session_factory,
        lease_timeout=timedelta(seconds=30),
    )

    definition_service = WorkflowDefinitionService(
        uow_factory=uow_factory,
        task_registry=task_registry,
        trigger_registry=trigger_registry,
    )

    start_service = WorkflowStartService(
        uow_factory=uow_factory,
        execution_queue=queue,
    )

    processing_service = TaskProcessingService(
        uow_factory=uow_factory,
        task_registry=task_registry,
    )

    definition_id = definition_service.create(
        CreateWorkflowDefinition(
            name="Diamond workflow",
            description="Worker end-to-end test",
            enabled=True,
            tasks=[
                CreateTaskDefinition(
                    plugin_type="produce_value",
                    key="produce",
                    configuration={
                        "value": "hello",
                    },
                    dependencies=[],
                    max_tries=1,
                ),
                CreateTaskDefinition(
                    plugin_type="collect_inputs",
                    key="collect-a",
                    configuration={},
                    dependencies=["produce"],
                    max_tries=1,
                ),
                CreateTaskDefinition(
                    plugin_type="collect_inputs",
                    key="collect-b",
                    configuration={},
                    dependencies=["produce"],
                    max_tries=1,
                ),
                CreateTaskDefinition(
                    plugin_type="collect_inputs",
                    key="collect",
                    configuration={},
                    dependencies=[
                        "collect-a",
                        "collect-b",
                    ],
                    max_tries=1,
                ),
            ],
            triggers=[],
        )
    )

    workflow_execution_id = start_service.start(definition_id)

    worker = Worker(
        worker_id=uuid4(),
        queue=queue,
        task_processing_service=processing_service,
        poll_interval=timedelta(milliseconds=10),
        heartbeat_interval=timedelta(milliseconds=50),
    )

    worker_thread = Thread(
        target=worker.run,
        name="test-worker",
    )
    worker_thread.start()

    try:
        workflow_execution = _wait_for_terminal_workflow(
            uow_factory,
            workflow_execution_id,
        )
    finally:
        worker.stop()
        worker_thread.join(timeout=2)

    assert not worker_thread.is_alive()
    assert workflow_execution.status is WorkflowStatus.COMPLETED

    tasks = {task.key: task for task in workflow_execution.task_executions}

    assert tasks.keys() == {
        "produce",
        "collect-a",
        "collect-b",
        "collect",
    }

    assert all(task.status is TaskStatus.COMPLETED for task in tasks.values())

    assert tasks["produce"].output.values == {
        "value": "hello",
    }

    assert tasks["collect-a"].output.values == {
        "produce": {
            "value": "hello",
        }
    }

    assert tasks["collect-b"].output.values == {
        "produce": {
            "value": "hello",
        }
    }

    assert tasks["collect"].output.values == {
        "collect-a": {
            "produce": {
                "value": "hello",
            }
        },
        "collect-b": {
            "produce": {
                "value": "hello",
            }
        },
    }


# ==================================================================================================
# Retry
# ==================================================================================================


def test_worker_retries_task_until_success(
    uow_factory,
    session_factory,
    task_registry,
):
    """A retryable task should be released, reclaimed, and eventually complete."""

    trigger_registry = TriggerRegistry()

    queue = PostgresExecutionQueue(
        session_factory=session_factory,
        lease_timeout=timedelta(seconds=30),
    )

    definition_service = WorkflowDefinitionService(
        uow_factory=uow_factory,
        task_registry=task_registry,
        trigger_registry=trigger_registry,
    )

    start_service = WorkflowStartService(
        uow_factory=uow_factory,
        execution_queue=queue,
    )

    processing_service = TaskProcessingService(
        uow_factory=uow_factory,
        task_registry=task_registry,
    )

    definition_id = definition_service.create(
        CreateWorkflowDefinition(
            name="Retry workflow",
            description="Worker retry end-to-end test",
            enabled=True,
            tasks=[
                CreateTaskDefinition(
                    plugin_type="fail_once",
                    key="retry-task",
                    configuration={},
                    dependencies=[],
                    max_tries=2,
                ),
            ],
            triggers=[],
        )
    )

    workflow_execution_id = start_service.start(definition_id)

    worker = Worker(
        worker_id=uuid4(),
        queue=queue,
        task_processing_service=processing_service,
        poll_interval=timedelta(milliseconds=10),
        heartbeat_interval=timedelta(milliseconds=50),
    )

    worker_thread = Thread(
        target=worker.run,
        name="test-retry-worker",
    )
    worker_thread.start()

    try:
        execution = _wait_for_terminal_workflow(
            uow_factory,
            workflow_execution_id,
        )
    finally:
        worker.stop()
        worker_thread.join(timeout=2)

    assert not worker_thread.is_alive()
    assert execution.status is WorkflowStatus.COMPLETED

    task = execution.task_executions[0]

    assert task.status is TaskStatus.COMPLETED
    assert task.output.values == {
        "result": "success",
    }


# ==================================================================================================
# Retry Exhaustion
# ==================================================================================================


def test_exhausted_retries_fail_workflow_and_cancel_remaining_tasks(
    uow_factory,
    session_factory,
    task_registry,
):
    """A terminal task failure should fail the workflow and cancel unfinished tasks."""

    trigger_registry = TriggerRegistry()

    queue = PostgresExecutionQueue(
        session_factory=session_factory,
        lease_timeout=timedelta(seconds=30),
    )

    definition_service = WorkflowDefinitionService(
        uow_factory=uow_factory,
        task_registry=task_registry,
        trigger_registry=trigger_registry,
    )

    start_service = WorkflowStartService(
        uow_factory=uow_factory,
        execution_queue=queue,
    )

    processing_service = TaskProcessingService(
        uow_factory=uow_factory,
        task_registry=task_registry,
    )

    definition_id = definition_service.create(
        CreateWorkflowDefinition(
            name="Failure workflow",
            description="Worker terminal-failure end-to-end test",
            enabled=True,
            tasks=[
                CreateTaskDefinition(
                    plugin_type="failing",
                    key="fail",
                    configuration={},
                    dependencies=[],
                    max_tries=1,
                ),
                CreateTaskDefinition(
                    plugin_type="successful",
                    key="child",
                    configuration={},
                    dependencies=["fail"],
                    max_tries=1,
                ),
            ],
            triggers=[],
        )
    )

    workflow_execution_id = start_service.start(definition_id)

    worker = Worker(
        worker_id=uuid4(),
        queue=queue,
        task_processing_service=processing_service,
        poll_interval=timedelta(milliseconds=10),
        heartbeat_interval=timedelta(milliseconds=50),
    )

    worker_thread = Thread(
        target=worker.run,
        name="test-failure-worker",
    )
    worker_thread.start()

    try:
        execution = _wait_for_terminal_workflow(
            uow_factory,
            workflow_execution_id,
        )
    finally:
        worker.stop()
        worker_thread.join(timeout=2)

    assert not worker_thread.is_alive()
    assert execution.status is WorkflowStatus.FAILED

    tasks = {task.key: task for task in execution.task_executions}

    assert tasks["fail"].status is TaskStatus.FAILED
    assert tasks["child"].status is TaskStatus.CANCELLED


# ==================================================================================================
# Stale Queue Entry
# ==================================================================================================


def test_cancelled_queued_task_does_not_execute(
    uow_factory,
    session_factory,
    task_registry,
    recording_task_type,
):
    """A stale queue entry for a cancelled task must not execute its plugin."""

    trigger_registry = TriggerRegistry()

    queue = PostgresExecutionQueue(
        session_factory=session_factory,
        lease_timeout=timedelta(seconds=30),
    )

    definition_service = WorkflowDefinitionService(
        uow_factory=uow_factory,
        task_registry=task_registry,
        trigger_registry=trigger_registry,
    )

    start_service = WorkflowStartService(
        uow_factory=uow_factory,
        execution_queue=queue,
    )

    processing_service = TaskProcessingService(
        uow_factory=uow_factory,
        task_registry=task_registry,
    )

    definition_id = definition_service.create(
        CreateWorkflowDefinition(
            name="Stale queue workflow",
            description="Cancelled queued task end-to-end test",
            enabled=True,
            tasks=[
                CreateTaskDefinition(
                    plugin_type="failing",
                    key="fail",
                    configuration={},
                    dependencies=[],
                    max_tries=1,
                ),
                CreateTaskDefinition(
                    plugin_type="recording",
                    key="recording",
                    configuration={},
                    dependencies=[],
                    max_tries=1,
                ),
            ],
            triggers=[],
        )
    )

    workflow_execution_id = start_service.start(definition_id)

    # Both tasks are roots, so both have queue entries. Process the failing
    # task directly so the workflow fails and its queued sibling is cancelled.
    execution = load_execution(
        uow_factory,
        workflow_execution_id,
    )

    failing_task = get_task(execution, "fail")

    processing_service.process(failing_task.id)

    execution = load_execution(
        uow_factory,
        workflow_execution_id,
    )

    recording_task = get_task(execution, "recording")

    assert execution.status is WorkflowStatus.FAILED
    assert recording_task.status is TaskStatus.CANCELLED
    assert recording_task_type.executions == 0

    # The queue still contains entries created when the workflow started.
    # Let the Worker consume them. The cancelled recording task must never
    # execute its plugin.
    worker = Worker(
        worker_id=uuid4(),
        queue=queue,
        task_processing_service=processing_service,
        poll_interval=timedelta(milliseconds=10),
        heartbeat_interval=timedelta(milliseconds=50),
    )

    worker_thread = Thread(
        target=worker.run,
        name="test-stale-entry-worker",
    )
    worker_thread.start()

    try:
        _wait_for_queue_to_become_idle(
            queue,
            worker._worker_id,
        )
    finally:
        worker.stop()
        worker_thread.join(timeout=2)

    execution = load_execution(
        uow_factory,
        workflow_execution_id,
    )

    recording_task = get_task(execution, "recording")

    assert not worker_thread.is_alive()
    assert execution.status is WorkflowStatus.FAILED
    assert recording_task.status is TaskStatus.CANCELLED
    assert recording_task_type.executions == 0


# ==================================================================================================
# Multiple Workers
# ==================================================================================================


def test_two_workers_process_sibling_tasks(
    uow_factory,
    session_factory,
    task_registry,
):
    """Multiple workers should safely process tasks from the same workflow."""

    trigger_registry = TriggerRegistry()

    queue = PostgresExecutionQueue(
        session_factory=session_factory,
        lease_timeout=timedelta(seconds=30),
    )

    definition_service = WorkflowDefinitionService(
        uow_factory=uow_factory,
        task_registry=task_registry,
        trigger_registry=trigger_registry,
    )

    start_service = WorkflowStartService(
        uow_factory=uow_factory,
        execution_queue=queue,
    )

    processing_service = TaskProcessingService(
        uow_factory=uow_factory,
        task_registry=task_registry,
    )

    definition_id = definition_service.create(
        CreateWorkflowDefinition(
            name="Two worker workflow",
            description="Multiple worker end-to-end test",
            enabled=True,
            tasks=[
                CreateTaskDefinition(
                    plugin_type="successful",
                    key="root",
                    configuration={},
                    dependencies=[],
                    max_tries=1,
                ),
                CreateTaskDefinition(
                    plugin_type="successful",
                    key="left",
                    configuration={},
                    dependencies=["root"],
                    max_tries=1,
                ),
                CreateTaskDefinition(
                    plugin_type="successful",
                    key="right",
                    configuration={},
                    dependencies=["root"],
                    max_tries=1,
                ),
                CreateTaskDefinition(
                    plugin_type="successful",
                    key="join",
                    configuration={},
                    dependencies=[
                        "left",
                        "right",
                    ],
                    max_tries=1,
                ),
            ],
            triggers=[],
        )
    )

    workflow_execution_id = start_service.start(definition_id)

    worker_a = Worker(
        worker_id=uuid4(),
        queue=queue,
        task_processing_service=processing_service,
        poll_interval=timedelta(milliseconds=10),
        heartbeat_interval=timedelta(milliseconds=50),
    )

    worker_b = Worker(
        worker_id=uuid4(),
        queue=queue,
        task_processing_service=processing_service,
        poll_interval=timedelta(milliseconds=10),
        heartbeat_interval=timedelta(milliseconds=50),
    )

    thread_a = Thread(
        target=worker_a.run,
        name="test-worker-a",
    )

    thread_b = Thread(
        target=worker_b.run,
        name="test-worker-b",
    )

    thread_a.start()
    thread_b.start()

    try:
        execution = _wait_for_terminal_workflow(
            uow_factory,
            workflow_execution_id,
        )
    finally:
        worker_a.stop()
        worker_b.stop()

        thread_a.join(timeout=2)
        thread_b.join(timeout=2)

    assert not thread_a.is_alive()
    assert not thread_b.is_alive()

    assert execution.status is WorkflowStatus.COMPLETED

    tasks = {task.key: task for task in execution.task_executions}

    assert tasks.keys() == {
        "root",
        "left",
        "right",
        "join",
    }

    assert all(task.status is TaskStatus.COMPLETED for task in tasks.values())


# ==================================================================================================
# Private Helpers
# ==================================================================================================


def _wait_for_terminal_workflow(
    uow_factory,
    workflow_execution_id,
    timeout: float = 5.0,
):
    """Wait for a WorkflowExecution to reach a terminal state."""

    deadline = monotonic() + timeout

    while monotonic() < deadline:
        with uow_factory() as uow:
            workflow_execution = uow.workflow_executions.load(workflow_execution_id)

        if workflow_execution.status in {
            WorkflowStatus.COMPLETED,
            WorkflowStatus.FAILED,
            WorkflowStatus.CANCELLED,
        }:
            return workflow_execution

        sleep(0.01)

    raise AssertionError(
        f"Workflow execution {workflow_execution_id} did not terminate within {timeout} seconds."
    )


def _wait_for_queue_to_become_idle(
    queue,
    worker_id,
    timeout: float = 2.0,
):
    """Wait until the worker has consumed all immediately claimable entries."""

    deadline = monotonic() + timeout

    while monotonic() < deadline:
        claim = queue.claim(worker_id)

        if claim is None:
            return

        # Do not steal work from the worker while checking. Return any claim
        # acquired by this probe immediately.
        queue.release(claim)

        sleep(0.01)

    raise AssertionError(f"Execution queue did not become idle within {timeout} seconds.")
