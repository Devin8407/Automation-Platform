"""Tests for the Reconciler runtime."""

from threading import Thread
from unittest.mock import Mock
from uuid import uuid4


def test_reconcile_enqueues_runnable_tasks(
    reconciler,
    mock_uow_factory,
    mock_execution_queue,
):
    task_ids = [
        uuid4(),
        uuid4(),
    ]

    unit_of_work = Mock()
    unit_of_work.workflow_executions.find_runnable_ids.return_value = task_ids

    mock_uow_factory.return_value.__enter__.return_value = unit_of_work

    reconciler._reconcile()

    unit_of_work.workflow_executions.find_runnable_ids.assert_called_once_with()
    mock_execution_queue.enqueue.assert_called_once_with(task_ids)


def test_reconcile_does_not_enqueue_when_no_tasks_are_runnable(
    reconciler,
    mock_uow_factory,
    mock_execution_queue,
):
    unit_of_work = Mock()
    unit_of_work.workflow_executions.find_runnable_ids.return_value = []

    mock_uow_factory.return_value.__enter__.return_value = unit_of_work

    reconciler._reconcile()

    unit_of_work.workflow_executions.find_runnable_ids.assert_called_once_with()
    mock_execution_queue.enqueue.assert_not_called()


def test_run_reconciles_repeatedly(
    reconciler,
    mock_uow_factory,
):
    unit_of_work = Mock()
    unit_of_work.workflow_executions.find_runnable_ids.return_value = []

    mock_uow_factory.return_value.__enter__.return_value = unit_of_work

    thread = Thread(target=reconciler.run)
    thread.start()

    _wait_until(lambda: unit_of_work.workflow_executions.find_runnable_ids.call_count >= 2)

    reconciler.stop()
    thread.join(timeout=1)

    assert not thread.is_alive()


def test_run_continues_after_reconciliation_failure(
    reconciler,
    mock_uow_factory,
):
    unit_of_work = Mock()

    unit_of_work.workflow_executions.find_runnable_ids.side_effect = [
        RuntimeError("database unavailable"),
        [],
    ]

    mock_uow_factory.return_value.__enter__.return_value = unit_of_work

    thread = Thread(target=reconciler.run)
    thread.start()

    _wait_until(lambda: unit_of_work.workflow_executions.find_runnable_ids.call_count >= 2)

    reconciler.stop()
    thread.join(timeout=1)

    assert not thread.is_alive()

    assert unit_of_work.workflow_executions.find_runnable_ids.call_count >= 2


def test_stop_causes_reconciler_to_exit(
    reconciler,
    mock_uow_factory,
):
    unit_of_work = Mock()
    unit_of_work.workflow_executions.find_runnable_ids.return_value = []

    mock_uow_factory.return_value.__enter__.return_value = unit_of_work

    thread = Thread(target=reconciler.run)
    thread.start()

    _wait_until(lambda: unit_of_work.workflow_executions.find_runnable_ids.called)

    reconciler.stop()
    thread.join(timeout=1)

    assert not thread.is_alive()


# ==================================================================================================
# Helpers
# ==================================================================================================


def _wait_until(
    condition,
    timeout: float = 1.0,
) -> None:
    """Wait until a condition becomes true."""

    from time import monotonic, sleep

    deadline = monotonic() + timeout

    while monotonic() < deadline:
        if condition():
            return

        sleep(0.001)

    raise AssertionError(f"Condition was not met within {timeout} seconds.")
