from datetime import timedelta
from unittest.mock import Mock

import pytest

from automation_platform.application import ChronologicalTriggerService
from automation_platform.runtime.scheduler import Scheduler


@pytest.fixture
def mock_chronological_trigger_service_dependency():
    """Return a mocked chronological trigger service dependency."""

    return Mock(spec=ChronologicalTriggerService)


@pytest.fixture
def mock_scheduler(
    mock_chronological_trigger_service_dependency,
) -> Scheduler:
    """Return a Scheduler with mocked dependencies."""

    return Scheduler(
        chronological_trigger_service=mock_chronological_trigger_service_dependency,
        poll_interval=timedelta(milliseconds=1),
    )


@pytest.fixture
def scheduler(
    chronological_trigger_service,
) -> Scheduler:
    """Return a Scheduler backed by real application services."""

    return Scheduler(
        chronological_trigger_service=chronological_trigger_service,
        poll_interval=timedelta(milliseconds=10),
    )
