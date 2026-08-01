"""Tests for queue bootstrap."""

from __future__ import annotations

from collections.abc import Callable

from automation_platform.config import Settings
from automation_platform.execution_queue.bootstrap import build_execution_queue
from automation_platform.execution_queue.postgres import PostgresExecutionQueue
from automation_platform.infrastructure import Infrastructure


def test_create_queue_returns_postgres_queue(
    infrastructure_factory: Callable[..., Infrastructure],
    settings_factory: Callable[..., Settings],
):
    """PostgreSQL backend constructs the PostgreSQL implementation."""

    settings = settings_factory(queue_type="postgres")

    infrastructure = infrastructure_factory(settings=settings)

    queue = build_execution_queue(infrastructure)

    assert isinstance(queue, PostgresExecutionQueue)


def test_create_queue_reuses_session_factory(
    infrastructure_factory: Callable[..., Infrastructure],
):
    """Bootstrap injects the shared SessionFactory."""

    infrastructure = infrastructure_factory()

    queue = build_execution_queue(infrastructure)

    assert queue._session_factory is infrastructure.session_factory


def test_create_queue_configures_lease_timeout(
    infrastructure_factory: Callable[..., Infrastructure],
):
    """Bootstrap configures the queue lease timeout from settings."""

    infrastructure = infrastructure_factory()

    queue = build_execution_queue(infrastructure)

    assert queue._lease_timeout == (infrastructure.settings.queue_lease_timeout)


def test_create_queue_returns_new_queue_instance(
    infrastructure_factory: Callable[..., Infrastructure],
):
    """Each bootstrap call constructs a new queue instance."""

    infrastructure = infrastructure_factory()

    first = build_execution_queue(infrastructure)
    second = build_execution_queue(infrastructure)

    assert first is not second
