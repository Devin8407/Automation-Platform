"""Scheduler runtime bootstrap."""

from __future__ import annotations

import logging
import signal
from types import FrameType

from ...application import ChronologicalTriggerService, WorkflowStartService
from ...config import load_settings
from ...execution_queue import build_execution_queue
from ...infrastructure import build_infrastructure
from ...observability import configure_logging
from ...persistence import build_unit_of_work_factory
from ...plugins.triggers import TriggerRegistry
from .scheduler import Scheduler

logger = logging.getLogger(__name__)


# ==================================================================================================
# Public API
# ==================================================================================================


def run_scheduler() -> None:
    """Construct and run a Scheduler runtime."""

    settings = load_settings()
    configure_logging(settings.log_level)

    infrastructure = build_infrastructure(settings)

    unit_of_work_factory = build_unit_of_work_factory(infrastructure)

    execution_queue = build_execution_queue(infrastructure)

    workflow_start_service = WorkflowStartService(
        uow_factory=unit_of_work_factory,
        execution_queue=execution_queue,
    )

    trigger_registry = TriggerRegistry()

    chronological_trigger_service = ChronologicalTriggerService(
        uow_factory=unit_of_work_factory,
        trigger_registry=trigger_registry,
        workflow_start_service=workflow_start_service,
    )

    scheduler = Scheduler(
        chronological_trigger_service=chronological_trigger_service,
        poll_interval=settings.scheduler_poll_interval,
    )

    _register_signal_handlers(scheduler)

    scheduler.run()


# ==================================================================================================
# Private helpers
# ==================================================================================================


def _register_signal_handlers(scheduler: Scheduler) -> None:
    """Register handlers for graceful Scheduler shutdown."""

    def handle_shutdown(
        signum: int,
        frame: FrameType | None,
    ) -> None:
        logger.info(
            "Received shutdown signal %s.",
            signal.Signals(signum).name,
        )
        scheduler.stop()

    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)
