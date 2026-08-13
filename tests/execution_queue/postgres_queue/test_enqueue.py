"""Integration tests for enqueue()."""

from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from automation_platform.execution_queue.postgres.model import QueueEntryModel


def test_enqueue_inserts_queue_entry(
    postgres_queue,
    session_factory,
    task_execution_factory,
):
    """Enqueuing a task inserts a corresponding queue entry."""

    task_execution = task_execution_factory()

    postgres_queue.enqueue([task_execution.id])

    with session_factory() as session:
        queue_entry = session.execute(
            select(QueueEntryModel).where(
                QueueEntryModel.task_execution_id == task_execution.id,
            )
        ).scalar_one()

        assert queue_entry.task_execution_id == task_execution.id
        assert queue_entry.claimed_by is None
        assert queue_entry.claim_token is None
        assert queue_entry.claimed_at is None
        assert queue_entry.last_heartbeat is None
        assert isinstance(queue_entry.queued_at, datetime)


def test_enqueue_sets_current_timestamp(
    postgres_queue,
    session_factory,
    task_execution_factory,
):
    """Enqueued tasks record the current UTC timestamp."""

    task_execution = task_execution_factory()

    before = datetime.now(timezone.utc)

    postgres_queue.enqueue([task_execution.id])

    after = datetime.now(timezone.utc)

    with session_factory() as session:
        queue_entry = session.execute(
            select(QueueEntryModel).where(
                QueueEntryModel.task_execution_id == task_execution.id,
            )
        ).scalar_one()

        assert before <= queue_entry.queued_at <= after


def test_enqueue_is_idempotent(
    postgres_queue,
    session_factory,
    task_execution_factory,
):
    """Enqueuing an already queued task has no effect."""

    task_execution = task_execution_factory()

    postgres_queue.enqueue([task_execution.id])
    postgres_queue.enqueue([task_execution.id])

    with session_factory() as session:
        entries = session.execute(
            select(QueueEntryModel).where(
                QueueEntryModel.task_execution_id == task_execution.id,
            )
        ).scalars()

        assert len(list(entries)) == 1


def test_enqueue_multiple_tasks(
    postgres_queue,
    session_factory,
    task_execution_factory,
):
    """Multiple task executions may be enqueued independently."""

    first_task = task_execution_factory()
    second_task = task_execution_factory()

    postgres_queue.enqueue([first_task.id])
    postgres_queue.enqueue([second_task.id])

    with session_factory() as session:
        entries = session.execute(select(QueueEntryModel)).scalars()

        queue_ids = {entry.task_execution_id for entry in entries}

        assert queue_ids == {
            first_task.id,
            second_task.id,
        }


def test_enqueue_preserves_existing_queue_entries(
    postgres_queue,
    session_factory,
    task_execution_factory,
):
    """Enqueuing a task does not modify existing queue entries."""

    first_task = task_execution_factory()
    second_task = task_execution_factory()

    postgres_queue.enqueue([first_task.id])

    with session_factory() as session:
        original = session.execute(
            select(QueueEntryModel).where(
                QueueEntryModel.task_execution_id == first_task.id,
            )
        ).scalar_one()

        original_time = original.queued_at

    postgres_queue.enqueue([second_task.id])

    with session_factory() as session:
        original = session.execute(
            select(QueueEntryModel).where(
                QueueEntryModel.task_execution_id == first_task.id,
            )
        ).scalar_one()

        assert original.queued_at == original_time


def test_enqueue_does_not_modify_existing_entry(
    postgres_queue,
    session_factory,
    task_execution_factory,
):
    """Repeated enqueue does not overwrite queue metadata."""

    task_execution = task_execution_factory()

    postgres_queue.enqueue([task_execution.id])

    with session_factory() as session:
        original = session.execute(
            select(QueueEntryModel).where(
                QueueEntryModel.task_execution_id == task_execution.id,
            )
        ).scalar_one()

        original_time = original.queued_at

    postgres_queue.enqueue([task_execution.id])

    with session_factory() as session:
        entry = session.execute(
            select(QueueEntryModel).where(
                QueueEntryModel.task_execution_id == task_execution.id,
            )
        ).scalar_one()

        assert entry.queued_at == original_time
        assert entry.claimed_by is None
        assert entry.claim_token is None


def test_enqueue_orders_tasks_by_enqueue_time(
    postgres_queue,
    session_factory,
    task_execution_factory,
):
    """Tasks retain FIFO ordering through their queued timestamp."""

    first_task = task_execution_factory()
    second_task = task_execution_factory()

    postgres_queue.enqueue([first_task.id])

    # Ensure timestamps differ.
    time.sleep(0.01)

    postgres_queue.enqueue([second_task.id])

    with session_factory() as session:
        entries = (
            session.execute(select(QueueEntryModel).order_by(QueueEntryModel.queued_at))
            .scalars()
            .all()
        )

        assert entries[0].task_execution_id == first_task.id
        assert entries[1].task_execution_id == second_task.id


def test_enqueue_sets_timestamp_close_to_now(
    postgres_queue,
    session_factory,
    task_execution_factory,
):
    """Queue timestamps are generated during enqueue."""

    task_execution = task_execution_factory()

    postgres_queue.enqueue([task_execution.id])

    with session_factory() as session:
        entry = session.execute(
            select(QueueEntryModel).where(
                QueueEntryModel.task_execution_id == task_execution.id,
            )
        ).scalar_one()

        assert datetime.now(timezone.utc) - entry.queued_at < timedelta(seconds=5)


def test_enqueue_is_idempotent_across_queue_instances(
    queue_factory,
    session_factory,
    task_execution_factory,
):
    """Concurrent queue instances enqueue a task only once."""

    task_execution = task_execution_factory()

    queue1 = queue_factory(queue_type="postgres")
    queue2 = queue_factory(queue_type="postgres")

    queue1.enqueue([task_execution.id])
    queue2.enqueue([task_execution.id])

    with session_factory() as session:
        entries = session.execute(
            select(QueueEntryModel).where(
                QueueEntryModel.task_execution_id == task_execution.id,
            )
        ).scalars()

        assert len(list(entries)) == 1
