"""Lease information for a claimed task execution."""

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class Claim:
    """Represents a worker's lease on a task execution.

    A claim is returned by the queue when a worker successfully claims a
    runnable task. It must be supplied when renewing the lease, releasing the
    task for retry, or completing the task.

    The claim token uniquely identifies the current lease, allowing the queue
    to detect when ownership has been lost due to lease expiration or
    reclamation by another worker.
    """

    task_execution_id: UUID
    claim_token: UUID
