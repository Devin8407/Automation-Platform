"""Queue fixtures."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from datetime import timedelta
from unittest.mock import Mock

import pytest

from automation_platform.config import Settings
from automation_platform.execution_queue import ExecutionQueue, build_execution_queue
from automation_platform.infrastructure import Infrastructure


@pytest.fixture
def postgres_queue(
    infrastructure_factory: Infrastructure,
) -> ExecutionQueue:
    """Create a queue for tests."""

    return build_execution_queue(infrastructure_factory())


@pytest.fixture
def queue_factory(
    infrastructure_factory: Callable[..., Infrastructure],
    settings_factory: Callable[..., Settings],
) -> Callable[..., ExecutionQueue]:
    """Create queues with customized infrastructure."""

    def factory(
        *,
        infrastructure: Infrastructure | None = None,
        settings: Settings | None = None,
        lease_timeout: timedelta | None = None,
        queue_type: str = "postgres",
    ) -> ExecutionQueue:
        if infrastructure is None:
            infrastructure = infrastructure_factory()

        if settings is None:
            settings = settings_factory(
                queue_type=queue_type,
            )

        if lease_timeout is not None:
            settings = replace(
                settings,
                queue_lease_timeout=lease_timeout,
            )

        infrastructure = replace(
            infrastructure,
            settings=settings,
        )

        return build_execution_queue(infrastructure)

    return factory


@pytest.fixture
def mock_execution_queue():
    return Mock(spec=ExecutionQueue)
