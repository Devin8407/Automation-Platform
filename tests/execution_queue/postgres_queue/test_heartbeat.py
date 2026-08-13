"""Integration tests for heartbeat()."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import select

from automation_platform.execution_queue.claims import Claim
from automation_platform.execution_queue.postgres.model import QueueEntryModel
from tests.helpers.postgres_queue import (
    create_claimed_postgres_queue_entry,
)


def test_heartbeat_renews_active_lease(
    postgres_queue,
    session_factory,
    task_execution_factory,
):
    """Heartbeat succeeds while the worker still owns the lease."""

    task_execution = task_execution_factory()
    worker_id = uuid4()

    postgres_queue.enqueue([task_execution.id])

    claim = postgres_queue.claim(worker_id)

    assert claim is not None

    assert postgres_queue.heartbeat(claim)


def test_heartbeat_updates_last_heartbeat_timestamp(
    postgres_queue,
    session_factory,
    task_execution_factory,
):
    """Heartbeat records the current heartbeat timestamp."""

    task_execution = task_execution_factory()

    postgres_queue.enqueue([task_execution.id])

    claim = postgres_queue.claim(uuid4())

    assert claim is not None

    before = datetime.now(timezone.utc)

    assert postgres_queue.heartbeat(claim)

    after = datetime.now(timezone.utc)

    with session_factory() as session:
        queue_entry = session.execute(
            select(QueueEntryModel).where(
                QueueEntryModel.task_execution_id == task_execution.id,
            )
        ).scalar_one()

        assert before <= queue_entry.last_heartbeat <= after


def test_heartbeat_does_not_modify_claimed_at(
    postgres_queue,
    session_factory,
    task_execution_factory,
):
    """Heartbeat does not modify when the lease was acquired."""

    task_execution = task_execution_factory()

    postgres_queue.enqueue([task_execution.id])

    claim = postgres_queue.claim(uuid4())

    assert claim is not None

    with session_factory() as session:
        claimed_at = session.execute(
            select(QueueEntryModel.claimed_at).where(
                QueueEntryModel.task_execution_id == task_execution.id,
            )
        ).scalar_one()

    assert postgres_queue.heartbeat(claim)

    with session_factory() as session:
        queue_entry = session.execute(
            select(QueueEntryModel).where(
                QueueEntryModel.task_execution_id == task_execution.id,
            )
        ).scalar_one()

        assert queue_entry.claimed_at == claimed_at


def test_heartbeat_returns_false_for_invalid_claim_token(
    postgres_queue,
    task_execution_factory,
):
    """Heartbeat fails if the claim token no longer matches."""

    task_execution = task_execution_factory()

    postgres_queue.enqueue([task_execution.id])

    claim = postgres_queue.claim(uuid4())

    assert claim is not None

    invalid_claim = Claim(
        task_execution_id=claim.task_execution_id,
        claim_token=uuid4(),
    )

    assert not postgres_queue.heartbeat(invalid_claim)


def test_heartbeat_returns_false_for_missing_queue_entry(
    postgres_queue,
):
    """Heartbeat fails if the queue entry no longer exists."""

    claim = Claim(
        task_execution_id=uuid4(),
        claim_token=uuid4(),
    )

    assert not postgres_queue.heartbeat(claim)


def test_heartbeat_returns_false_after_release(
    postgres_queue,
    task_execution_factory,
):
    """Heartbeat fails once the lease has been released."""

    task_execution = task_execution_factory()

    postgres_queue.enqueue([task_execution.id])

    claim = postgres_queue.claim(uuid4())

    assert claim is not None

    postgres_queue.release(claim)

    assert not postgres_queue.heartbeat(claim)


def test_heartbeat_returns_false_after_finish(
    postgres_queue,
    task_execution_factory,
):
    """Heartbeat fails once the task has been removed from the queue."""

    task_execution = task_execution_factory()

    postgres_queue.enqueue([task_execution.id])

    claim = postgres_queue.claim(uuid4())

    assert claim is not None

    postgres_queue.finish(claim, [])

    assert not postgres_queue.heartbeat(claim)


def test_heartbeat_does_not_reclaim_expired_lease(
    postgres_queue,
    session_factory,
    task_execution_factory,
):
    """Heartbeat never changes lease ownership."""

    task_execution = task_execution_factory()

    expired = datetime.now(timezone.utc) - timedelta(hours=1)

    with session_factory() as session:
        create_claimed_postgres_queue_entry(
            session,
            task_execution_id=task_execution.id,
            claimed_at=expired,
            last_heartbeat=expired,
        )

        original = session.execute(
            select(QueueEntryModel).where(
                QueueEntryModel.task_execution_id == task_execution.id,
            )
        ).scalar_one()

        claim = Claim(
            task_execution_id=task_execution.id,
            claim_token=original.claim_token,
        )

    assert postgres_queue.heartbeat(claim)

    with session_factory() as session:
        queue_entry = session.execute(
            select(QueueEntryModel).where(
                QueueEntryModel.task_execution_id == task_execution.id,
            )
        ).scalar_one()

        assert queue_entry.claimed_by == original.claimed_by
        assert queue_entry.claim_token == original.claim_token
