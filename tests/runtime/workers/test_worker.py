"""Tests for the Worker runtime."""

from threading import Event, Thread
from uuid import uuid4

from automation_platform.application import ProcessTaskResult


def test_process_claim_processes_task_and_finishes_claim(
    worker,
    claim,
    mock_execution_queue,
    task_processing_service_mock,
):
    runnable_task_ids = [uuid4(), uuid4()]

    task_processing_service_mock.process.return_value = ProcessTaskResult(
        enqueue_task_ids=runnable_task_ids,
        should_retry=False,
    )

    worker._process_claim(claim)

    task_processing_service_mock.process.assert_called_once_with(claim.task_execution_id)
    mock_execution_queue.release.assert_not_called()
    mock_execution_queue.finish.assert_called_once_with(
        claim,
        runnable_task_ids,
    )


def test_process_claim_releases_claim_when_task_should_retry(
    worker,
    claim,
    mock_execution_queue,
    task_processing_service_mock,
):
    task_processing_service_mock.process.return_value = ProcessTaskResult(
        enqueue_task_ids=[],
        should_retry=True,
    )

    worker._process_claim(claim)

    task_processing_service_mock.process.assert_called_once_with(claim.task_execution_id)
    mock_execution_queue.release.assert_called_once_with(claim)
    mock_execution_queue.finish.assert_not_called()


def test_process_claim_does_not_dispose_untrusted_claim(
    worker,
    claim,
    mock_execution_queue,
    task_processing_service_mock,
):
    processing_started = Event()
    allow_processing_to_finish = Event()

    def process(_):
        processing_started.set()
        allow_processing_to_finish.wait(timeout=1)

        return ProcessTaskResult(
            enqueue_task_ids=[],
            should_retry=False,
        )

    task_processing_service_mock.process.side_effect = process
    mock_execution_queue.heartbeat.return_value = False

    thread = Thread(
        target=worker._process_claim,
        args=(claim,),
    )
    thread.start()

    assert processing_started.wait(timeout=1)

    # Give the heartbeat enough time to observe the lost claim.
    assert _wait_until(lambda: mock_execution_queue.heartbeat.called)

    allow_processing_to_finish.set()
    thread.join(timeout=1)

    assert not thread.is_alive()
    mock_execution_queue.release.assert_not_called()
    mock_execution_queue.finish.assert_not_called()


def test_process_claim_does_not_dispose_claim_when_heartbeat_raises(
    worker,
    claim,
    mock_execution_queue,
    task_processing_service_mock,
):
    processing_started = Event()
    allow_processing_to_finish = Event()

    def process(_):
        processing_started.set()
        allow_processing_to_finish.wait(timeout=1)

        return ProcessTaskResult(
            enqueue_task_ids=[],
            should_retry=False,
        )

    task_processing_service_mock.process.side_effect = process
    mock_execution_queue.heartbeat.side_effect = RuntimeError("heartbeat failed")

    thread = Thread(
        target=worker._process_claim,
        args=(claim,),
    )
    thread.start()

    assert processing_started.wait(timeout=1)

    assert _wait_until(lambda: mock_execution_queue.heartbeat.called)

    allow_processing_to_finish.set()
    thread.join(timeout=1)

    assert not thread.is_alive()
    mock_execution_queue.release.assert_not_called()
    mock_execution_queue.finish.assert_not_called()


def test_heartbeat_repeats_until_stopped(
    worker,
    claim,
    mock_execution_queue,
):
    stop_event = Event()
    claim_untrusted_event = Event()

    mock_execution_queue.heartbeat.return_value = True

    thread = Thread(
        target=worker._heartbeat,
        args=(
            claim,
            stop_event,
            claim_untrusted_event,
        ),
    )
    thread.start()

    assert _wait_until(lambda: mock_execution_queue.heartbeat.call_count >= 2)

    stop_event.set()
    thread.join(timeout=1)

    assert not thread.is_alive()
    assert not claim_untrusted_event.is_set()


def test_heartbeat_marks_claim_untrusted_when_lease_is_lost(
    worker,
    claim,
    mock_execution_queue,
):
    stop_event = Event()
    claim_untrusted_event = Event()

    mock_execution_queue.heartbeat.return_value = False

    worker._heartbeat(
        claim,
        stop_event,
        claim_untrusted_event,
    )

    mock_execution_queue.heartbeat.assert_called_once_with(claim)
    assert claim_untrusted_event.is_set()


def test_heartbeat_marks_claim_untrusted_when_heartbeat_raises(
    worker,
    claim,
    mock_execution_queue,
):
    stop_event = Event()
    claim_untrusted_event = Event()

    mock_execution_queue.heartbeat.side_effect = RuntimeError("heartbeat failed")

    worker._heartbeat(
        claim,
        stop_event,
        claim_untrusted_event,
    )

    mock_execution_queue.heartbeat.assert_called_once_with(claim)
    assert claim_untrusted_event.is_set()


def test_stop_causes_idle_worker_to_exit(
    worker,
    mock_execution_queue,
):
    mock_execution_queue.claim.return_value = None

    thread = Thread(target=worker.run)
    thread.start()

    assert _wait_until(lambda: mock_execution_queue.claim.called)

    worker.stop()
    thread.join(timeout=1)

    assert not thread.is_alive()


def test_worker_claims_and_processes_task(
    worker,
    claim,
    mock_execution_queue,
    task_processing_service_mock,
):
    mock_execution_queue.claim.side_effect = [
        claim,
        None,
    ]

    task_processing_service_mock.process.return_value = ProcessTaskResult(
        enqueue_task_ids=[],
        should_retry=False,
    )

    thread = Thread(target=worker.run)
    thread.start()

    assert _wait_until(lambda: mock_execution_queue.finish.called)

    worker.stop()
    thread.join(timeout=1)

    mock_execution_queue.claim.assert_any_call(worker._worker_id)
    task_processing_service_mock.process.assert_called_once_with(claim.task_execution_id)
    mock_execution_queue.finish.assert_called_once_with(
        claim,
        [],
    )


def test_stop_during_processing_finishes_current_claim_before_exiting(
    worker,
    claim,
    mock_execution_queue,
    task_processing_service_mock,
):
    processing_started = Event()
    allow_processing_to_finish = Event()

    mock_execution_queue.claim.side_effect = [
        claim,
        None,
    ]

    def process(_):
        processing_started.set()
        allow_processing_to_finish.wait(timeout=1)

        return ProcessTaskResult(
            enqueue_task_ids=[],
            should_retry=False,
        )

    task_processing_service_mock.process.side_effect = process

    thread = Thread(target=worker.run)
    thread.start()

    assert processing_started.wait(timeout=1)

    worker.stop()

    assert thread.is_alive()

    allow_processing_to_finish.set()
    thread.join(timeout=1)

    assert not thread.is_alive()
    mock_execution_queue.finish.assert_called_once_with(
        claim,
        [],
    )


def test_processing_exception_does_not_dispose_claim(
    worker,
    claim,
    mock_execution_queue,
    task_processing_service_mock,
):
    task_processing_service_mock.process.side_effect = RuntimeError("processing failed")

    worker._process_claim(claim)

    mock_execution_queue.release.assert_not_called()
    mock_execution_queue.finish.assert_not_called()


# ==================================================================================================
# Helpers
# ==================================================================================================


def _wait_until(
    condition,
    timeout: float = 1.0,
) -> bool:
    """Wait until a condition becomes true."""

    completed = Event()

    def check():
        while not condition():
            if completed.wait(0.001):
                return

        completed.set()

    thread = Thread(target=check)
    thread.start()

    succeeded = completed.wait(timeout)

    completed.set()
    thread.join()

    return succeeded
