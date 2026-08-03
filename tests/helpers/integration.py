"""End-to-end tests for Worker workflow execution."""

from __future__ import annotations

from time import monotonic, sleep

from automation_platform.domain import WorkflowStatus

# ==================================================================================================
# Public API
# ==================================================================================================


def load_execution(uow_factory, workflow_execution_id):
    """Load a workflow execution using real persistence."""

    with uow_factory() as uow:
        return uow.workflow_executions.load(workflow_execution_id)


def get_task(execution, key):
    """Return a task execution by key."""

    return next(task for task in execution.task_executions if task.key == key)


def wait_for_terminal_workflow(
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
