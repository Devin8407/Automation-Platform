"""Integration tests for release()."""

from __future__ import annotations

from uuid import uuid4

from sqlalchemy import select

from automation_platform.execution_queue.claims import Claim
from automation_platform.execution_queue.postgres._model import QueueEntryModel


def test_release_clears_lease_metadata(
    postgres_queue,
    session_factory,
    task_execution_factory,
):
    """Release removes all lease metadata from the queue entry."""

    task_execution = task_execution_factory()

    postgres_queue.enqueue(task_execution.id)

    claim = postgres_queue.claim(uuid4())

    assert claim is not None

    postgres_queue.release(claim)

    with session_factory() as session:
        queue_entry = session.execute(
            select(QueueEntryModel).where(
                QueueEntryModel.task_execution_id == task_execution.id,
            )
        ).scalar_one()

        assert queue_entry.claimed_by is None
        assert queue_entry.claim_token is None
        assert queue_entry.claimed_at is None
        assert queue_entry.last_heartbeat is None


def test_release_preserves_queued_timestamp(
    postgres_queue,
    session_factory,
    task_execution_factory,
):
    """Release does not modify when the task was originally queued."""

    task_execution = task_execution_factory()

    postgres_queue.enqueue(task_execution.id)

    claim = postgres_queue.claim(uuid4())

    assert claim is not None

    with session_factory() as session:
        queued_at = session.execute(
            select(QueueEntryModel.queued_at).where(
                QueueEntryModel.task_execution_id == task_execution.id,
            )
        ).scalar_one()

    postgres_queue.release(claim)

    with session_factory() as session:
        queue_entry = session.execute(
            select(QueueEntryModel).where(
                QueueEntryModel.task_execution_id == task_execution.id,
            )
        ).scalar_one()

        assert queue_entry.queued_at == queued_at


def test_release_makes_task_immediately_claimable(
    postgres_queue,
    task_execution_factory,
):
    """Released tasks become immediately available for another worker."""

    task_execution = task_execution_factory()

    postgres_queue.enqueue(task_execution.id)

    first_claim = postgres_queue.claim(uuid4())

    assert first_claim is not None

    postgres_queue.release(first_claim)

    second_claim = postgres_queue.claim(uuid4())

    assert second_claim is not None
    assert second_claim.task_execution_id == task_execution.id
    assert second_claim.claim_token != first_claim.claim_token


def test_release_with_invalid_claim_token_has_no_effect(
    postgres_queue,
    session_factory,
    task_execution_factory,
):
    """Release ignores stale claim tokens."""

    task_execution = task_execution_factory()

    postgres_queue.enqueue(task_execution.id)

    claim = postgres_queue.claim(uuid4())

    assert claim is not None

    invalid_claim = Claim(
        task_execution_id=claim.task_execution_id,
        claim_token=uuid4(),
    )

    postgres_queue.release(invalid_claim)

    with session_factory() as session:
        queue_entry = session.execute(
            select(QueueEntryModel).where(
                QueueEntryModel.task_execution_id == task_execution.id,
            )
        ).scalar_one()

        assert queue_entry.claim_token == claim.claim_token
        assert queue_entry.claimed_by is not None
        assert queue_entry.claimed_at is not None
        assert queue_entry.last_heartbeat is not None


def test_release_missing_queue_entry_has_no_effect(
    postgres_queue,
):
    """Release is a no-op if the queue entry no longer exists."""

    claim = Claim(
        task_execution_id=uuid4(),
        claim_token=uuid4(),
    )

    postgres_queue.release(claim)


def test_release_is_idempotent(
    postgres_queue,
    session_factory,
    task_execution_factory,
):
    """Repeated release calls leave the queue in a valid state."""

    task_execution = task_execution_factory()

    postgres_queue.enqueue(task_execution.id)

    claim = postgres_queue.claim(uuid4())

    assert claim is not None

    postgres_queue.release(claim)
    postgres_queue.release(claim)

    with session_factory() as session:
        queue_entry = session.execute(
            select(QueueEntryModel).where(
                QueueEntryModel.task_execution_id == task_execution.id,
            )
        ).scalar_one()

        assert queue_entry.claimed_by is None
        assert queue_entry.claim_token is None
        assert queue_entry.claimed_at is None
        assert queue_entry.last_heartbeat is None


def test_release_allows_multiple_reclaims(
    postgres_queue,
    task_execution_factory,
):
    """Tasks may be claimed repeatedly after successive releases."""

    task_execution = task_execution_factory()

    postgres_queue.enqueue(task_execution.id)

    first_claim = postgres_queue.claim(uuid4())
    assert first_claim is not None

    postgres_queue.release(first_claim)

    second_claim = postgres_queue.claim(uuid4())
    assert second_claim is not None

    postgres_queue.release(second_claim)

    third_claim = postgres_queue.claim(uuid4())
    assert third_claim is not None

    assert third_claim.task_execution_id == task_execution.id


def test_release_does_not_change_task_identity(
    postgres_queue,
    session_factory,
    task_execution_factory,
):
    """Release never modifies the queued task."""

    task_execution = task_execution_factory()

    postgres_queue.enqueue(task_execution.id)

    claim = postgres_queue.claim(uuid4())

    assert claim is not None

    postgres_queue.release(claim)

    with session_factory() as session:
        queue_entry = session.execute(
            select(QueueEntryModel).where(
                QueueEntryModel.task_execution_id == task_execution.id,
            )
        ).scalar_one()

        assert queue_entry.task_execution_id == task_execution.id


def test_release_preserves_fifo_order(
    postgres_queue,
    task_execution_factory,
):
    """Released tasks retain their original queue position."""

    first_task = task_execution_factory()
    second_task = task_execution_factory()

    postgres_queue.enqueue(first_task.id)
    postgres_queue.enqueue(second_task.id)

    first_claim = postgres_queue.claim(uuid4())

    assert first_claim is not None

    postgres_queue.release(first_claim)

    second_claim = postgres_queue.claim(uuid4())

    assert second_claim is not None
    assert second_claim.task_execution_id == first_task.id
