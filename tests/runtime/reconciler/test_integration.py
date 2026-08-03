"""End-to-end tests for Worker workflow execution."""

from __future__ import annotations

from datetime import timedelta
from threading import Thread
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
from automation_platform.runtime import Reconciler
from automation_platform.runtime.worker import Worker
from tests.helpers import get_task, load_execution, wait_for_terminal_workflow

# ==================================================================================================
# Reconciliation
# ==================================================================================================


class DropFirstEnqueueQueue:
    """Execution queue that simulates losing the initial enqueue."""

    def __init__(self, queue):
        self._queue = queue
        self._drop_next_enqueue = True

    def enqueue(self, task_execution_ids):
        if self._drop_next_enqueue:
            self._drop_next_enqueue = False
            return

        self._queue.enqueue(task_execution_ids)

    def __getattr__(self, name):
        return getattr(self._queue, name)


def test_reconciler_recovers_stranded_workflow(
    uow_factory,
    session_factory,
):
    """Runnable persisted work should recover when its initial enqueue is lost."""

    task_registry = TaskRegistry()
    trigger_registry = TriggerRegistry()

    queue = PostgresExecutionQueue(
        session_factory=session_factory,
        lease_timeout=timedelta(seconds=30),
    )

    dropping_queue = DropFirstEnqueueQueue(queue)

    definition_service = WorkflowDefinitionService(
        uow_factory=uow_factory,
        task_registry=task_registry,
        trigger_registry=trigger_registry,
    )

    start_service = WorkflowStartService(
        uow_factory=uow_factory,
        execution_queue=dropping_queue,
    )

    processing_service = TaskProcessingService(
        uow_factory=uow_factory,
        task_registry=task_registry,
    )

    definition_id = definition_service.create(
        CreateWorkflowDefinition(
            name="Reconciliation workflow",
            description="Recover a lost initial queue entry",
            enabled=True,
            tasks=[
                CreateTaskDefinition(
                    plugin_type="produce_value",
                    key="produce",
                    configuration={
                        "value": "recovered",
                    },
                    dependencies=[],
                    max_tries=1,
                ),
            ],
            triggers=[],
        )
    )

    workflow_execution_id = start_service.start(definition_id)

    # WorkflowStartService committed the runnable task to persistence, but
    # DropFirstEnqueueQueue deliberately discarded its initial queue entry.
    execution = load_execution(
        uow_factory,
        workflow_execution_id,
    )

    task = get_task(execution, "produce")

    assert execution.status is WorkflowStatus.RUNNING
    assert task.status is TaskStatus.PENDING
    assert task.remaining_dependencies == 0

    # The real PostgreSQL queue should still be empty.
    assert queue.claim(uuid4()) is None

    worker = Worker(
        worker_id=uuid4(),
        queue=queue,
        task_processing_service=processing_service,
        poll_interval=timedelta(milliseconds=10),
        heartbeat_interval=timedelta(milliseconds=50),
    )

    reconciler = Reconciler(
        unit_of_work_factory=uow_factory,
        queue=queue,
        interval=timedelta(milliseconds=10),
    )

    worker_thread = Thread(
        target=worker.run,
        name="test-reconciliation-worker",
    )

    reconciler_thread = Thread(
        target=reconciler.run,
        name="test-reconciler",
    )

    worker_thread.start()
    reconciler_thread.start()

    try:
        execution = wait_for_terminal_workflow(
            uow_factory,
            workflow_execution_id,
        )
    finally:
        reconciler.stop()
        worker.stop()

        reconciler_thread.join(timeout=2)
        worker_thread.join(timeout=2)

    assert not reconciler_thread.is_alive()
    assert not worker_thread.is_alive()

    assert execution.status is WorkflowStatus.COMPLETED

    task = get_task(execution, "produce")

    assert task.status is TaskStatus.COMPLETED
    assert task.output.values == {
        "value": "recovered",
    }
