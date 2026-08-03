"""Worker runtime bootstrap."""

from __future__ import annotations

import logging
import signal
from types import FrameType
from uuid import uuid4

from ...application import TaskProcessingService
from ...config import load_settings
from ...execution_queue import build_execution_queue
from ...infrastructure import build_infrastructure
from ...observability import configure_logging
from ...persistence import build_unit_of_work_factory
from ...plugins.tasks import TaskRegistry
from .worker import Worker

logger = logging.getLogger(__name__)

# ==================================================================================================
# Public API
# ==================================================================================================


def run_worker() -> None:
    """Construct and run a Worker runtime."""

    settings = load_settings()
    configure_logging(settings.log_level)

    infrastructure = build_infrastructure(settings)

    unit_of_work_factory = build_unit_of_work_factory(infrastructure)

    task_registry = TaskRegistry()

    task_processing_service = TaskProcessingService(
        unit_of_work_factory=unit_of_work_factory,
        task_registry=task_registry,
    )

    execution_queue = build_execution_queue(infrastructure)

    worker = Worker(
        worker_id=uuid4(),
        queue=execution_queue,
        task_processing_service=task_processing_service,
        poll_interval=settings.worker_poll_interval,
        heartbeat_interval=settings.worker_heartbeat_interval,
    )

    _register_signal_handlers(worker)

    worker.run()


# ==================================================================================================
# Private helpers
# ==================================================================================================


def _register_signal_handlers(worker: Worker) -> None:
    """Register handlers for graceful Worker shutdown."""

    def handle_shutdown(
        signum: int,
        frame: FrameType | None,
    ) -> None:
        logger.info(
            "Received shutdown signal %s.",
            signal.Signals(signum).name,
        )
        worker.stop()

    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)
