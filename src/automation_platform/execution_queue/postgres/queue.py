"""Queue abstraction for scheduling runnable task executions."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from sqlalchemy import delete, or_, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session, sessionmaker

from ..claims import Claim
from ..interface import ExecutionQueue
from ._model import QueueEntryModel


class PostgresExecutionQueue(ExecutionQueue):
    """Technology-independent interface for managing runnable task executions."""

    # ==============================================================================================
    # Constructor
    # ==============================================================================================

    def __init__(
        self,
        session_factory: sessionmaker[Session],
        lease_timeout: timedelta,
    ) -> None:
        self._session_factory = session_factory
        self._lease_timeout = lease_timeout

    # ==============================================================================================
    # Public API
    # ==============================================================================================

    def enqueue(self, task_execution_id: Iterable[UUID]) -> None:
        """Ensure a runnable task execution is present in the queue.

        If the task execution is already queued, the operation has no effect.

        Args:
            task_execution_id: Identifier of the task execution to enqueue.
        """

        with self._session_factory() as session:
            self._insert_queue_entries(
                session,
                task_execution_id,
                datetime.now(timezone.utc),
            )

            session.commit()

    def claim(self, worker_id: UUID) -> Claim | None:
        """Atomically claim the next available task execution.

        The returned claim represents a lease on the task. Workers must
        periodically renew the lease using heartbeat while executing
        the task.

        Args:
            worker_id: Identifier of the worker requesting work.

        Returns:
            A claim for the next runnable task execution, or None if no
            runnable work is currently available.
        """

        now = datetime.now(timezone.utc)
        expiration = now - self._lease_timeout

        with self._session_factory() as session:
            queue_entry = session.execute(
                select(QueueEntryModel)
                .where(
                    or_(
                        QueueEntryModel.claimed_by.is_(None),
                        QueueEntryModel.last_heartbeat <= expiration,
                    )
                )
                .order_by(QueueEntryModel.queued_at)
                .limit(1)
                .with_for_update(skip_locked=True)
            ).scalar_one_or_none()

            if queue_entry is None:
                session.commit()
                return None

            queue_entry.claimed_by = worker_id
            queue_entry.claim_token = uuid4()
            queue_entry.claimed_at = now
            queue_entry.last_heartbeat = now

            claim = Claim(
                task_execution_id=queue_entry.task_execution_id,
                claim_token=queue_entry.claim_token,
            )

            session.commit()

            return claim

    def heartbeat(self, claim: Claim) -> bool:
        """Renew the lease for a claimed task execution.

        Args:
            claim: Claim representing the worker's current lease.

        Returns:
            True if the lease was successfully renewed, or False if
            the lease has already been lost or reclaimed by another worker.
        """

        now = datetime.now(timezone.utc)

        with self._session_factory() as session:
            result = session.execute(
                update(QueueEntryModel)
                .where(
                    QueueEntryModel.task_execution_id == claim.task_execution_id,
                    QueueEntryModel.claim_token == claim.claim_token,
                )
                .values(last_heartbeat=now)
            )

            session.commit()

            return result.rowcount == 1

    def release(self, claim: Claim) -> None:
        """Release a claimed task execution back to the queue.

        This is typically used when task execution should be retried. The task
        remains in the queue but immediately becomes available for another
        worker to claim.

        If the claim has already been lost, this operation has no effect.

        Args:
            claim: Claim representing the worker's current lease.
        """

        with self._session_factory() as session:
            session.execute(
                update(QueueEntryModel)
                .where(
                    QueueEntryModel.task_execution_id == claim.task_execution_id,
                    QueueEntryModel.claim_token == claim.claim_token,
                )
                .values(
                    claim_token=None,
                    claimed_by=None,
                    claimed_at=None,
                    last_heartbeat=None,
                )
            )

            session.commit()

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

        now = datetime.now(timezone.utc)

        with self._session_factory() as session:
            result = session.execute(
                delete(QueueEntryModel).where(
                    QueueEntryModel.task_execution_id == claim.task_execution_id,
                    QueueEntryModel.claim_token == claim.claim_token,
                )
            )

            if result.rowcount == 1:
                self._insert_queue_entries(session, runnable_task_ids, now)

            session.commit()

    # ==============================================================================================
    # Private Helpers
    # ==============================================================================================

    def _insert_queue_entries(
        self,
        session: Session,
        task_execution_ids: Iterable[UUID],
        queued_at: datetime,
    ) -> None:
        """Ensure task executions are present in the queue.

        Queue entries are inserted only if they do not already exist, making the
        operation idempotent. All newly inserted entries receive the same queued
        timestamp.

        Args:
            session: Database session used for the operation.
            task_execution_ids: Identifiers of the task executions to enqueue.
            queued_at: Timestamp recorded for newly inserted queue entries.
        """

        if not task_execution_ids:
            return

        stmt = (
            insert(QueueEntryModel)
            .values(
                [
                    {
                        "task_execution_id": task_id,
                        "claim_token": None,
                        "claimed_by": None,
                        "queued_at": queued_at,
                        "claimed_at": None,
                        "last_heartbeat": None,
                    }
                    for task_id in task_execution_ids
                ]
            )
            .on_conflict_do_nothing(
                index_elements=["task_execution_id"],
            )
        )

        session.execute(stmt)
