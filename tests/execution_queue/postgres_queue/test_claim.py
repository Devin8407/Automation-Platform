"""Integration tests for claim()."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import select

from automation_platform.execution_queue.postgres._model import QueueEntryModel
from tests.helpers.postgres_queue import (
    create_claimed_postgres_queue_entry,
    create_postgres_queue_entry,
)


def test_claim_returns_none_when_queue_empty(
    postgres_queue,
):
    """Claim returns None when no runnable work exists."""

    claim = postgres_queue.claim(uuid4())

    assert claim is None


def test_claim_returns_oldest_available_task(
    postgres_queue,
    session_factory,
    task_execution_factory,
):
    """Workers claim the oldest runnable task."""

    older = datetime.now(timezone.utc) - timedelta(minutes=10)
    newer = datetime.now(timezone.utc)

    first_task = task_execution_factory()
    second_task = task_execution_factory()

    with session_factory() as session:
        create_postgres_queue_entry(
            session,
            task_execution_id=second_task.id,
            queued_at=newer,
        )

        create_postgres_queue_entry(
            session,
            task_execution_id=first_task.id,
            queued_at=older,
        )

    claim = postgres_queue.claim(uuid4())

    assert claim is not None
    assert claim.task_execution_id == first_task.id


def test_claim_marks_task_as_claimed(
    postgres_queue,
    session_factory,
    task_execution_factory,
):
    """Claiming a task records lease metadata."""

    task_execution = task_execution_factory()

    postgres_queue.enqueue(task_execution.id)

    worker_id = uuid4()

    claim = postgres_queue.claim(worker_id)

    assert claim is not None

    with session_factory() as session:
        queue_entry = session.execute(
            select(QueueEntryModel).where(
                QueueEntryModel.task_execution_id == task_execution.id,
            )
        ).scalar_one()

        assert queue_entry.claimed_by == worker_id
        assert queue_entry.claim_token == claim.claim_token
        assert queue_entry.claimed_at is not None
        assert queue_entry.last_heartbeat is not None


def test_claim_removes_task_from_future_claims(
    postgres_queue,
    task_execution_factory,
):
    """Claimed tasks cannot immediately be claimed again."""

    postgres_queue.enqueue(task_execution_factory().id)

    first_claim = postgres_queue.claim(uuid4())

    second_claim = postgres_queue.claim(uuid4())

    assert first_claim is not None
    assert second_claim is None


def test_claim_claims_second_task_when_first_is_claimed(
    postgres_queue,
    task_execution_factory,
):
    """Workers continue claiming remaining runnable tasks."""

    task_execution = task_execution_factory()

    second_task = task_execution_factory()

    postgres_queue.enqueue(task_execution.id)
    postgres_queue.enqueue(second_task.id)

    first = postgres_queue.claim(uuid4())
    second = postgres_queue.claim(uuid4())

    assert first is not None
    assert second is not None

    assert {
        first.task_execution_id,
        second.task_execution_id,
    } == {
        task_execution.id,
        second_task.id,
    }


def test_claim_reclaims_expired_lease(
    queue_factory,
    session_factory,
    task_execution_factory,
):
    """Expired leases become runnable again."""

    task_execution = task_execution_factory()

    queue = queue_factory(lease_timeout=timedelta(seconds=30), queue_type="postgres")

    expired = datetime.now(timezone.utc) - timedelta(minutes=5)

    with session_factory() as session:
        create_claimed_postgres_queue_entry(
            session,
            task_execution_id=task_execution.id,
            claimed_at=expired,
            last_heartbeat=expired,
        )

    claim = queue.claim(uuid4())

    assert claim is not None
    assert claim.task_execution_id == task_execution.id


def test_claim_does_not_reclaim_active_lease(
    queue_factory,
    infrastructure_factory,
    session_factory,
    task_execution_factory,
):
    """Active leases are not reclaimed."""

    infrastructure = infrastructure_factory()

    postgres_queue = queue_factory(
        infrastructure=infrastructure, lease_timeout=timedelta(minutes=5), queue_type="postgres"
    )

    now = datetime.now(timezone.utc)

    with session_factory() as session:
        create_claimed_postgres_queue_entry(
            session,
            task_execution_id=task_execution_factory().id,
            claimed_at=now,
            last_heartbeat=now,
        )

    claim = postgres_queue.claim(uuid4())

    assert claim is None


def test_claim_generates_new_claim_token(
    postgres_queue,
    task_execution_factory,
):
    """Each successful claim receives a unique lease token."""

    postgres_queue.enqueue(task_execution_factory().id)

    claim = postgres_queue.claim(uuid4())

    assert claim is not None
    assert claim.claim_token is not None


def test_claim_updates_heartbeat_timestamp(
    postgres_queue,
    session_factory,
    task_execution_factory,
):
    """Claim initializes the lease heartbeat."""

    task_execution = task_execution_factory()

    before = datetime.now(timezone.utc)

    postgres_queue.enqueue(task_execution.id)

    claim = postgres_queue.claim(uuid4())

    after = datetime.now(timezone.utc)

    assert claim is not None

    with session_factory() as session:
        queue_entry = session.execute(
            select(QueueEntryModel).where(
                QueueEntryModel.task_execution_id == task_execution.id,
            )
        ).scalar_one()

        assert before <= queue_entry.last_heartbeat <= after


def test_claim_updates_claim_timestamp(
    postgres_queue,
    session_factory,
    task_execution_factory,
):
    """Claim records when the lease was acquired."""

    task_execution = task_execution_factory()

    before = datetime.now(timezone.utc)

    postgres_queue.enqueue(task_execution.id)

    claim = postgres_queue.claim(uuid4())

    after = datetime.now(timezone.utc)

    assert claim is not None

    with session_factory() as session:
        queue_entry = session.execute(
            select(QueueEntryModel).where(
                QueueEntryModel.task_execution_id == task_execution.id,
            )
        ).scalar_one()

        assert before <= queue_entry.claimed_at <= after


def test_concurrent_workers_only_one_claims_single_task(
    postgres_queue,
    task_execution_factory,
):
    """Only one worker can claim a task."""

    task_execution = task_execution_factory()

    postgres_queue.enqueue(task_execution.id)

    def claim():
        return postgres_queue.claim(uuid4())

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: claim(), range(2)))

    claims = [claim for claim in results if claim is not None]

    assert len(claims) == 1
    assert claims[0].task_execution_id == task_execution.id


def test_concurrent_workers_claim_different_tasks(
    postgres_queue,
    task_execution_factory,
):
    """Concurrent workers claim different runnable tasks."""

    first_task = task_execution_factory()
    second_task = task_execution_factory()

    postgres_queue.enqueue(first_task.id)
    postgres_queue.enqueue(second_task.id)

    def claim():
        return postgres_queue.claim(uuid4())

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: claim(), range(2)))

    claims = [claim for claim in results if claim is not None]

    assert len(claims) == 2

    assert {claim.task_execution_id for claim in claims} == {
        first_task.id,
        second_task.id,
    }


def test_claim_skips_already_claimed_tasks(
    postgres_queue,
    task_execution_factory,
):
    """Claim skips leased tasks and returns the next available task."""

    first_task = task_execution_factory()
    second_task = task_execution_factory()

    postgres_queue.enqueue(first_task.id)
    postgres_queue.enqueue(second_task.id)

    first_claim = postgres_queue.claim(uuid4())

    assert first_claim is not None
    assert first_claim.task_execution_id == first_task.id

    second_claim = postgres_queue.claim(uuid4())

    assert second_claim is not None
    assert second_claim.task_execution_id == second_task.id


def test_claim_skips_already_claimed_task(
    postgres_queue,
    task_execution_factory,
):
    """Claim skips leased tasks and returns the next runnable task."""

    first_task = task_execution_factory()
    second_task = task_execution_factory()

    postgres_queue.enqueue(first_task.id)
    postgres_queue.enqueue(second_task.id)

    first_claim = postgres_queue.claim(uuid4())

    assert first_claim is not None
    assert first_claim.task_execution_id == first_task.id

    second_claim = postgres_queue.claim(uuid4())

    assert second_claim is not None
    assert second_claim.task_execution_id == second_task.id


def test_multiple_queue_instances_claim_distinct_tasks(
    queue_factory,
    task_execution_factory,
):
    """Independent workers claim different runnable tasks."""

    first_task = task_execution_factory()
    second_task = task_execution_factory()

    queue1 = queue_factory(queue_type="postgres")
    queue2 = queue_factory(queue_type="postgres")

    queue1.enqueue(first_task.id)
    queue1.enqueue(second_task.id)

    first_claim = queue1.claim(uuid4())
    second_claim = queue2.claim(uuid4())

    assert first_claim is not None
    assert second_claim is not None

    assert {
        first_claim.task_execution_id,
        second_claim.task_execution_id,
    } == {
        first_task.id,
        second_task.id,
    }


def test_multiple_workers_claim_all_tasks_once(
    queue_factory,
    task_execution_factory,
):
    """Multiple workers drain the queue without duplicate claims."""

    tasks = [
        task_execution_factory(),
        task_execution_factory(),
        task_execution_factory(),
        task_execution_factory(),
    ]

    queue = queue_factory(queue_type="postgres")

    for task in tasks:
        queue.enqueue(task.id)

    claimed = set()

    for _ in range(len(tasks)):
        worker_queue = queue_factory(queue_type="postgres")

        claim = worker_queue.claim(uuid4())

        assert claim is not None
        assert claim.task_execution_id not in claimed

        claimed.add(claim.task_execution_id)

    assert claimed == {task.id for task in tasks}

    assert queue_factory(queue_type="postgres").claim(uuid4()) is None
