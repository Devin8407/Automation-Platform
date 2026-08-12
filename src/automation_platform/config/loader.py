"""Application configuration loader."""

from __future__ import annotations

import os
from datetime import timedelta

from .settings import Settings

# ==================================================================================================
# Public API
# ==================================================================================================


def load_settings() -> Settings:
    """Load application settings from environment variables."""

    queue_lease_timeout = _get_float("QUEUE_LEASE_TIMEOUT_SECONDS", default=30.0)
    worker_poll_interval = _get_float("WORKER_POLL_INTERVAL_SECONDS", default=1.0)
    worker_heartbeat_interval = _get_float("WORKER_HEARTBEAT_INTERVAL_SECONDS", default=10.0)
    scheduler_poll_interval = _get_float("SCHEDULER_POLL_INTERVAL", default=1.0)
    reconciliation_interval = _get_float("RECONCILIATION_INTERVAL_SECONDS", default=30.0)

    _validate_timing(
        queue_lease_timeout,
        worker_poll_interval,
        worker_heartbeat_interval,
        scheduler_poll_interval,
        reconciliation_interval,
    )

    return Settings(
        database_url=_get_required("DATABASE_URL"),
        echo_sql=_get_bool("ECHO_SQL", default=False),
        queue_type=os.getenv("QUEUE_TYPE", "postgres"),
        queue_lease_timeout=timedelta(seconds=queue_lease_timeout),
        worker_poll_interval=timedelta(seconds=worker_poll_interval),
        worker_heartbeat_interval=timedelta(seconds=worker_heartbeat_interval),
        scheduler_poll_interval=timedelta(seconds=scheduler_poll_interval),
        reconciliation_interval=timedelta(seconds=reconciliation_interval),
        api_host=os.getenv("API_HOST", "0.0.0.0"),
        api_port=os.getenv("API_PORT", "8000"),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
    )


# ==================================================================================================
# Private Helpers
# ==================================================================================================


def _get_required(name: str) -> str:
    value = os.getenv(name)

    if value is None or not value.strip():
        raise ValueError(f"Required environment variable {name!r} is not set.")

    return value


def _get_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)

    if value is None:
        return default

    normalized = value.strip().lower()

    if normalized == "true":
        return True

    if normalized == "false":
        return False

    raise ValueError(f"Environment variable {name!r} must be 'true' or 'false'.")


def _get_float(name: str, default: float) -> float:
    value = os.getenv(name)

    if value is None:
        return default

    try:
        return float(value)
    except ValueError as exc:
        raise ValueError(f"Environment variable {name!r} must be a number.") from exc


def _validate_timing(
    queue_lease_timeout: float,
    worker_poll_interval: float,
    worker_heartbeat_interval: float,
    scheduler_poll_interval: float,
    reconciliation_interval: float,
) -> None:
    """Raise an exception if configuration timings are invalid"""

    if not queue_lease_timeout > 0:
        raise ValueError(f"queue lease timeout {queue_lease_timeout} is not greater than 0.")

    if not worker_poll_interval > 0:
        raise ValueError(f"worker poll interval {worker_poll_interval} is not greater than 0.")

    if not worker_heartbeat_interval > 0:
        raise ValueError(
            f"worker heartbeat interval {worker_heartbeat_interval} is not greater than 0."
        )

    if not scheduler_poll_interval > 0:
        raise ValueError(
            f"scheduler poll interval {scheduler_poll_interval} is not greater than 0."
        )

    if not reconciliation_interval > 0:
        raise ValueError(
            f"reconciliation interval {reconciliation_interval} is not greater than 0."
        )

    if queue_lease_timeout < 3 * worker_heartbeat_interval:
        raise ValueError(
            f"queue lease timeout {queue_lease_timeout} must be at least "
            f"3x worker heartbeat interval {worker_heartbeat_interval}."
        )
