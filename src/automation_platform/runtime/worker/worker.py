"""Worker runtime."""

from __future__ import annotations

import logging
from datetime import timedelta
from threading import Event, Thread
from uuid import UUID

from ...application.task_processing import TaskProcessingService
from ...execution_queue import Claim, ExecutionQueue

logger = logging.getLogger(__name__)


class Worker:
    """Runtime responsible for processing queued task executions."""

    # ==============================================================================================
    # Constructor
    # ==============================================================================================

    def __init__(
        self,
        worker_id: UUID,
        queue: ExecutionQueue,
        task_processing_service: TaskProcessingService,
        poll_interval: timedelta,
        heartbeat_interval: timedelta,
    ) -> None:
        self._worker_id = worker_id
        self._queue = queue
        self._task_processing_service = task_processing_service
        self._poll_interval = poll_interval
        self._heartbeat_interval = heartbeat_interval

        self._stop_event = Event()

    # ==============================================================================================
    # Public API
    # ==============================================================================================

    def run(self) -> None:
        """Run the worker until stopped."""

        logger.info("Worker %s started", self._worker_id)

        try:
            while not self._stop_event.is_set():
                claim = self._queue.claim(self._worker_id)

                if claim is None:
                    self._stop_event.wait(self._poll_interval.total_seconds())
                    continue

                self._process_claim(claim)

        finally:
            logger.info("Worker %s stopped", self._worker_id)

    def stop(self) -> None:
        """Request graceful worker shutdown.

        The worker stops claiming new work. If a task is currently being
        processed, processing is allowed to reach its normal safe boundary.
        """

        self._stop_event.set()

    # ==============================================================================================
    # Private Helpers
    # ==============================================================================================

    def _process_claim(self, claim: Claim) -> None:
        """Process one claimed task execution."""

        heartbeat_stop_event = Event()
        claim_untrusted_event = Event()

        heartbeat_thread = Thread(
            target=self._heartbeat,
            args=(
                claim,
                heartbeat_stop_event,
                claim_untrusted_event,
            ),
            name=f"worker-heartbeat-{claim.task_execution_id}",
            daemon=True,
        )

        heartbeat_thread.start()

        try:
            result = self._task_processing_service.process(claim.task_execution_id)
        except Exception:
            logger.exception(
                "Unexpected error processing task execution %s",
                claim.task_execution_id,
            )
            return
        finally:
            heartbeat_stop_event.set()
            heartbeat_thread.join()

        if claim_untrusted_event.is_set():
            logger.warning(
                "Worker %s no longer trusts its claim for task execution %s",
                self._worker_id,
                claim.task_execution_id,
            )
            return

        if result.should_retry:
            self._queue.release(claim)
            return

        self._queue.finish(
            claim,
            result.enqueue_task_ids,
        )

    def _heartbeat(
        self,
        claim: Claim,
        stop_event: Event,
        claim_untrusted_event: Event,
    ) -> None:
        """Maintain the lease for one claimed task execution."""

        interval = self._heartbeat_interval.total_seconds()

        while not stop_event.wait(interval):
            try:
                lease_owned = self._queue.heartbeat(claim)
            except Exception:
                logger.exception(
                    "Heartbeat failed for task execution %s",
                    claim.task_execution_id,
                )
                claim_untrusted_event.set()
                return

            if not lease_owned:
                claim_untrusted_event.set()
                return
