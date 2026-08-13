"""Reconciliation runtime bootstrap."""

from __future__ import annotations

import logging
import signal
from types import FrameType

from ...config import load_settings
from ...execution_queue import build_execution_queue
from ...infrastructure import build_infrastructure
from ...observability import configure_logging
from ...persistence import build_unit_of_work_factory
from .reconciler import Reconciler

logger = logging.getLogger(__name__)


# ==================================================================================================
# Public API
# ==================================================================================================


def run_reconciler() -> None:
    """Construct and run the Reconciliation runtime."""

    settings = load_settings()
    configure_logging(settings.log_level)

    infrastructure = build_infrastructure(settings)

    unit_of_work_factory = build_unit_of_work_factory(infrastructure)

    execution_queue = build_execution_queue(infrastructure)

    reconciler = Reconciler(
        unit_of_work_factory=unit_of_work_factory,
        queue=execution_queue,
        interval=settings.reconciliation_interval,
    )

    _register_signal_handlers(reconciler)

    reconciler.run()


# ==================================================================================================
# Private Helpers
# ==================================================================================================


def _register_signal_handlers(reconciler: Reconciler) -> None:
    """Register handlers for graceful Reconciler shutdown."""

    def handle_shutdown(
        signum: int,
        _frame: FrameType | None,
    ) -> None:
        logger.info(
            "Received shutdown signal %s",
            signal.Signals(signum).name,
        )
        reconciler.stop()

    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)
