"""Helpers for integration tests."""

from __future__ import annotations

from time import monotonic, sleep

from automation_platform.application import (
    ChronologicalTriggerService,
    TriggerInitializationService,
    WorkflowDefinitionService,
    WorkflowStartService,
)
from automation_platform.domain import WorkflowStatus
from automation_platform.persistence.chronological_triggers.model import (
    ChronologicalTriggerStateModel,
)

# ==================================================================================================
# Application Service Composition
# ==================================================================================================


def create_workflow_definition_service(
    *,
    uow_factory,
    task_registry,
    trigger_registry,
    execution_queue,
) -> WorkflowDefinitionService:
    """Create a fully wired workflow definition service.

    Args:
        uow_factory: Factory for creating persistence units of work.
        task_registry: Registry of available task plugins.
        trigger_registry: Registry of available trigger plugins.
        execution_queue: Execution queue used when starting workflows.

    Returns:
        Fully configured workflow definition service.
    """

    workflow_start_service = WorkflowStartService(
        uow_factory=uow_factory,
        execution_queue=execution_queue,
    )

    chronological_trigger_service = ChronologicalTriggerService(
        uow_factory=uow_factory,
        trigger_registry=trigger_registry,
        workflow_start_service=workflow_start_service,
    )

    trigger_initialization_service = TriggerInitializationService(
        chronological_trigger_service=chronological_trigger_service,
    )

    return WorkflowDefinitionService(
        uow_factory=uow_factory,
        task_registry=task_registry,
        trigger_registry=trigger_registry,
        trigger_initialization_service=trigger_initialization_service,
    )


# ==================================================================================================
# Persistence
# ==================================================================================================


def load_execution(
    uow_factory,
    workflow_execution_id,
):
    """Load a workflow execution using real persistence."""

    with uow_factory() as uow:
        return uow.workflow_executions.load(workflow_execution_id)


def get_task(
    execution,
    key,
):
    """Return a task execution by key."""

    return next(task for task in execution.task_executions if task.key == key)


def load_chronological_trigger_state(
    session_factory,
    trigger_definition_id,
):
    """Load chronological trigger state using real persistence."""

    with session_factory() as session:
        return session.get(
            ChronologicalTriggerStateModel,
            trigger_definition_id,
        )


# ==================================================================================================
# Waiting
# ==================================================================================================


def wait_for_terminal_workflow(
    uow_factory,
    workflow_execution_id,
    timeout: float = 5.0,
):
    """Wait for a workflow execution to reach a terminal state."""

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


def wait_for_queue_to_become_idle(
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
