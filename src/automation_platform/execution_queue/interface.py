"""Queue abstraction for scheduling runnable task executions."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Protocol
from uuid import UUID

from .claims import Claim


class ExecutionQueue(Protocol):
    """Technology-independent interface for managing runnable task executions."""

    # ==============================================================================================
    # Public API
    # ==============================================================================================

    def enqueue(self, task_execution_id: UUID) -> None:
        """Adds a task execution to the queue

        Args:
            task_execution_id: Identifier of the task execution to enqueue.
        """

        ...

    def claim(self, worker_id: UUID) -> Claim | None:
        """Atomically claim the next available task execution.

        The returned claim represents a lease on the task. Workers must
        periodically renew the lease using :meth:`heartbeat` while executing
        the task.

        Args:
            worker_id: Identifier of the worker requesting work.

        Returns:
            A claim for the next runnable task execution, or None if no
            runnable work is currently available.
        """

        ...

    def heartbeat(self, claim: Claim) -> bool:
        """Renew the lease for a claimed task execution.

        Args:
            claim: Claim representing the worker's current lease.

        Returns:
            True if the lease was successfully renewed, or False if
            the lease has already been lost or reclaimed by another worker.
        """

        ...

    def release(self, claim: Claim) -> None:
        """Release a claimed task execution back to the queue.

        This is typically used when task execution should be retried. The task
        remains in the queue but immediately becomes available for another
        worker to claim.

        If the claim has already been lost, this operation has no effect.

        Args:
            claim: Claim representing the worker's current lease.
        """

    def finish(self, claim: Claim, runnable_task_ids: Iterable[UUID]) -> None:
        """Complete a claimed task execution.

        This operation atomically verifies ownership of the claim, removes the
        completed task from the queue, and enqueues any newly runnable task
        executions.

        If the claim has already been lost, this operation has no effect.

        Args:
            claim: Claim representing the worker's current lease.
            runnable_task_ids: Identifiers of task executions that became
                runnable as a result of completing the current task.
        """

        ...
