"""Chronological trigger scheduler runtime."""

from __future__ import annotations

import logging
from datetime import timedelta
from threading import Event

from ...application import ChronologicalTriggerService

logger = logging.getLogger(__name__)


class Scheduler:
    """Runtime responsible for processing due chronological triggers.

    The Scheduler continuously asks the Application Layer to process due
    chronological trigger occurrences. It waits only when no work is
    currently available.
    """

    def __init__(
        self,
        chronological_trigger_service: ChronologicalTriggerService,
        poll_interval: timedelta,
    ) -> None:
        """Initialize the Scheduler.

        Args:
            chronological_trigger_service: Application service used to process
                due chronological triggers.
            poll_interval: Time to wait when no chronological trigger is due.
        """

        self._chronological_trigger_service = chronological_trigger_service
        self._poll_interval = poll_interval

        self._stop_event = Event()

    # ==============================================================================================
    # Public API
    # ==============================================================================================

    def run(self) -> None:
        """Process chronological triggers until stopped."""

        logger.info("Scheduler started")

        try:
            while not self._stop_event.is_set():
                try:
                    processed = self._chronological_trigger_service.process_next_due()
                except Exception:
                    logger.exception("Scheduled trigger processing failed")
                    self._stop_event.wait(self._poll_interval.total_seconds())
                    continue

                if not processed:
                    self._stop_event.wait(self._poll_interval.total_seconds())
        finally:
            logger.info("Scheduler stopped")

    def stop(self) -> None:
        """Request graceful Scheduler shutdown."""

        self._stop_event.set()
