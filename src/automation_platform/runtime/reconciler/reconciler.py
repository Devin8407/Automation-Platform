"""Reconciliation runtime."""

from __future__ import annotations

import logging
from datetime import timedelta
from threading import Event
from typing import Callable

from ...execution_queue import ExecutionQueue
from ...persistence import UnitOfWork

logger = logging.getLogger(__name__)


class Reconciler:
    """Runtime responsible for repairing missing queue entries.

    The Reconciler periodically discovers task executions that are durably
    runnable in persistence and ensures they are present in the execution
    queue.
    """

    def __init__(
        self,
        unit_of_work_factory: Callable[[], UnitOfWork],
        queue: ExecutionQueue,
        interval: timedelta,
    ) -> None:
        self._unit_of_work_factory = unit_of_work_factory
        self._queue = queue
        self._interval = interval

        self._stop_event = Event()

    # ==============================================================================================
    # Public API
    # ==============================================================================================

    def run(self) -> None:
        """Run reconciliation cycles until stopped."""

        logger.info("Reconciler started")

        try:
            while not self._stop_event.is_set():
                try:
                    self._reconcile()
                except Exception:
                    logger.exception("Reconciliation cycle failed")

                self._stop_event.wait(self._interval.total_seconds())
        finally:
            logger.info("Reconciler stopped")

    def stop(self) -> None:
        """Request graceful Reconciler shutdown."""

        self._stop_event.set()

    # ==============================================================================================
    # Private Helpers
    # ==============================================================================================

    def _reconcile(self) -> None:
        """Ensure durably runnable task executions are queued."""

        with self._unit_of_work_factory() as uow:
            runnable_task_ids = uow.workflow_executions.find_runnable_ids()

        if not runnable_task_ids:
            return

        self._queue.enqueue(runnable_task_ids)

        logger.info(
            "Reconciled %d runnable task executions",
            len(runnable_task_ids),
        )
