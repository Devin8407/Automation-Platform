"""Tests for the Scheduler runtime."""

from threading import Thread


def test_run_processes_due_triggers_repeatedly(
    mock_scheduler,
    mock_chronological_trigger_service_dependency,
):
    """Available chronological triggers should be processed continuously."""

    mock_chronological_trigger_service_dependency.process_next_due.return_value = True

    thread = Thread(target=mock_scheduler.run)
    thread.start()

    _wait_until(
        lambda: mock_chronological_trigger_service_dependency.process_next_due.call_count >= 2
    )

    mock_scheduler.stop()
    thread.join(timeout=1)

    assert not thread.is_alive()

    assert mock_chronological_trigger_service_dependency.process_next_due.call_count >= 2


def test_run_polls_again_when_no_trigger_is_due(
    mock_scheduler,
    mock_chronological_trigger_service_dependency,
):
    """The Scheduler should poll again when no trigger is currently due."""

    mock_chronological_trigger_service_dependency.process_next_due.return_value = False

    thread = Thread(target=mock_scheduler.run)
    thread.start()

    _wait_until(
        lambda: mock_chronological_trigger_service_dependency.process_next_due.call_count >= 2
    )

    mock_scheduler.stop()
    thread.join(timeout=1)

    assert not thread.is_alive()

    assert mock_chronological_trigger_service_dependency.process_next_due.call_count >= 2


def test_run_continues_after_trigger_processing_failure(
    mock_scheduler,
    mock_chronological_trigger_service_dependency,
):
    """A processing failure should not terminate the Scheduler."""

    mock_chronological_trigger_service_dependency.process_next_due.side_effect = [
        RuntimeError("database unavailable"),
        False,
    ]

    thread = Thread(target=mock_scheduler.run)
    thread.start()

    _wait_until(
        lambda: mock_chronological_trigger_service_dependency.process_next_due.call_count >= 2
    )

    mock_scheduler.stop()
    thread.join(timeout=1)

    assert not thread.is_alive()

    assert mock_chronological_trigger_service_dependency.process_next_due.call_count >= 2


def test_stop_causes_scheduler_to_exit(
    mock_scheduler,
    mock_chronological_trigger_service_dependency,
):
    """Stopping the Scheduler should cause its run loop to exit."""

    mock_chronological_trigger_service_dependency.process_next_due.return_value = False

    thread = Thread(target=mock_scheduler.run)
    thread.start()

    _wait_until(lambda: mock_chronological_trigger_service_dependency.process_next_due.called)

    mock_scheduler.stop()
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
