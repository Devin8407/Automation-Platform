"""Reconciler test fixtures."""

from datetime import timedelta

import pytest

from automation_platform.runtime.reconciler import Reconciler


@pytest.fixture
def reconciler(
    mock_uow_factory,
    mock_execution_queue,
):
    return Reconciler(
        unit_of_work_factory=mock_uow_factory,
        queue=mock_execution_queue,
        interval=timedelta(milliseconds=10),
    )
