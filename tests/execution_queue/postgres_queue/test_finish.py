"""Integration tests for finish()."""

from __future__ import annotations

from uuid import uuid4

from sqlalchemy import select

from automation_platform.execution_queue.claims import Claim
from automation_platform.execution_queue.postgres.model import QueueEntryModel


def test_finish_removes_completed_task_from_queue(
    postgres_queue,
    session_factory,
    task_execution_factory,
):
    """Finishing a task removes it from the queue."""

    task_execution = task_execution_factory()

    postgres_queue.enqueue([task_execution.id])

    claim = postgres_queue.claim(uuid4())

    assert claim is not None

    postgres_queue.finish(claim, [])

    with session_factory() as session:
        entries = session.execute(
            select(QueueEntryModel).where(
                QueueEntryModel.task_execution_id == task_execution.id,
            )
        ).scalars()

        assert len(list(entries)) == 0


def test_finish_enqueues_runnable_children(
    postgres_queue,
    session_factory,
    task_execution_factory,
):
    """Runnable child tasks are enqueued during finish."""

    task_execution = task_execution_factory()
    child = task_execution_factory()

    postgres_queue.enqueue([task_execution.id])

    claim = postgres_queue.claim(uuid4())

    assert claim is not None

    postgres_queue.finish(
        claim,
        [child.id],
    )

    with session_factory() as session:
        child_entry = session.execute(
            select(QueueEntryModel).where(
                QueueEntryModel.task_execution_id == child.id,
            )
        ).scalar_one()

        assert child_entry.task_execution_id == child.id
        assert child_entry.claimed_by is None
        assert child_entry.claim_token is None


def test_finish_removes_parent_and_enqueues_children_atomically(
    postgres_queue,
    session_factory,
    task_execution_factory,
):
    """Finished tasks are removed while children are queued."""

    task_execution = task_execution_factory()
    child = task_execution_factory()

    postgres_queue.enqueue([task_execution.id])

    claim = postgres_queue.claim(uuid4())

    assert claim is not None

    postgres_queue.finish(
        claim,
        [child.id],
    )

    with session_factory() as session:
        entries = session.execute(select(QueueEntryModel)).scalars().all()

        assert len(entries) == 1
        assert entries[0].task_execution_id == child.id


def test_finish_with_invalid_claim_does_nothing(
    postgres_queue,
    session_factory,
    task_execution_factory,
):
    """Lost leases do not modify the queue."""

    task_execution = task_execution_factory()
    child = task_execution_factory()

    postgres_queue.enqueue([task_execution.id])

    claim = postgres_queue.claim(uuid4())

    assert claim is not None

    invalid_claim = Claim(
        task_execution_id=claim.task_execution_id,
        claim_token=uuid4(),
    )

    postgres_queue.finish(
        invalid_claim,
        [child.id],
    )

    with session_factory() as session:
        parent = session.execute(
            select(QueueEntryModel).where(
                QueueEntryModel.task_execution_id == task_execution.id,
            )
        ).scalar_one()

        children = session.execute(
            select(QueueEntryModel).where(
                QueueEntryModel.task_execution_id == child.id,
            )
        ).scalars()

        assert parent.claim_token == claim.claim_token
        assert len(list(children)) == 0


def test_finish_is_idempotent(
    postgres_queue,
    session_factory,
    task_execution_factory,
):
    """Repeated finish calls leave the queue in a valid state."""

    task_execution = task_execution_factory()

    postgres_queue.enqueue([task_execution.id])

    claim = postgres_queue.claim(uuid4())

    assert claim is not None

    postgres_queue.finish(claim, [])
    postgres_queue.finish(claim, [])

    with session_factory() as session:
        entries = session.execute(select(QueueEntryModel)).scalars()

        assert len(list(entries)) == 0


def test_finish_duplicate_children_are_ignored(
    postgres_queue,
    session_factory,
    task_execution_factory,
):
    """Duplicate runnable tasks are only enqueued once."""

    task_execution = task_execution_factory()
    child = task_execution_factory()

    postgres_queue.enqueue([task_execution.id])

    claim = postgres_queue.claim(uuid4())

    assert claim is not None

    postgres_queue.finish(
        claim,
        [
            child.id,
            child.id,
        ],
    )

    with session_factory() as session:
        entries = session.execute(
            select(QueueEntryModel).where(
                QueueEntryModel.task_execution_id == child.id,
            )
        ).scalars()

        assert len(list(entries)) == 1


def test_finish_handles_empty_runnable_tasks(
    postgres_queue,
    session_factory,
    task_execution_factory,
):
    """Finishing with no runnable children simply removes the task."""

    task_execution = task_execution_factory()

    postgres_queue.enqueue([task_execution.id])

    claim = postgres_queue.claim(uuid4())

    assert claim is not None

    postgres_queue.finish(claim, [])

    with session_factory() as session:
        assert session.execute(select(QueueEntryModel)).scalars().first() is None


def test_finish_preserves_existing_queue_entries(
    postgres_queue,
    session_factory,
    task_execution_factory,
):
    """Finishing one task does not affect unrelated queued tasks."""

    task_execution = task_execution_factory()
    unrelated = task_execution_factory()

    postgres_queue.enqueue([task_execution.id])
    postgres_queue.enqueue([unrelated.id])

    claim = postgres_queue.claim(uuid4())

    assert claim is not None

    postgres_queue.finish(claim, [])

    with session_factory() as session:
        entries = session.execute(select(QueueEntryModel)).scalars().all()

        assert len(entries) == 1
        assert entries[0].task_execution_id == unrelated.id


def test_finish_does_not_duplicate_existing_children(
    postgres_queue,
    session_factory,
    task_execution_factory,
):
    """Children already in the queue are not enqueued again."""

    parent = task_execution_factory()
    child = task_execution_factory()

    postgres_queue.enqueue([parent.id])
    postgres_queue.enqueue([child.id])

    claim = postgres_queue.claim(uuid4())

    assert claim is not None

    postgres_queue.finish(
        claim,
        [child.id],
    )

    with session_factory() as session:
        entries = session.execute(
            select(QueueEntryModel).where(
                QueueEntryModel.task_execution_id == child.id,
            )
        ).scalars()

        assert len(list(entries)) == 1


def test_finish_does_not_duplicate_already_queued_child(
    postgres_queue,
    session_factory,
    task_execution_factory,
):
    """Existing queued children are not duplicated."""

    parent = task_execution_factory()
    child = task_execution_factory()

    postgres_queue.enqueue([parent.id])
    postgres_queue.enqueue([child.id])

    claim = postgres_queue.claim(uuid4())

    assert claim is not None

    postgres_queue.finish(
        claim,
        [child.id],
    )

    with session_factory() as session:
        entries = session.execute(
            select(QueueEntryModel).where(
                QueueEntryModel.task_execution_id == child.id,
            )
        ).scalars()

        assert len(list(entries)) == 1
