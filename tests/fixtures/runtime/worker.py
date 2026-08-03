"""Worker test fixtures."""

from datetime import timedelta
from unittest.mock import Mock
from uuid import uuid4

import pytest

from automation_platform.application import TaskProcessingService
from automation_platform.execution_queue import Claim
from automation_platform.runtime.worker import Worker


@pytest.fixture
def worker_id():
    return uuid4()


@pytest.fixture
def claim():
    return Claim(
        task_execution_id=uuid4(),
        claim_token=uuid4(),
    )


@pytest.fixture
def task_processing_service_mock():
    """Return a mocked task processing service."""

    return Mock(spec=TaskProcessingService)


@pytest.fixture
def worker(
    worker_id,
    mock_execution_queue,
    task_processing_service_mock,
):
    return Worker(
        worker_id=worker_id,
        queue=mock_execution_queue,
        task_processing_service=task_processing_service_mock,
        poll_interval=timedelta(milliseconds=10),
        heartbeat_interval=timedelta(milliseconds=10),
    )
