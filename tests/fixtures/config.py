from collections.abc import Callable
from datetime import timedelta

import pytest

from automation_platform.config import Settings


@pytest.fixture
def settings_factory() -> Callable[..., Settings]:
    """Create settings for tests."""

    def factory(
        *,
        database_url: str = "postgresql+psycopg://automation:password@localhost:5432/automation_test",
        echo_sql: bool = False,
        queue_type: str = "postgres",
        queue_lease_timeout: timedelta | None = timedelta(seconds=30),
        worker_poll_interval: timedelta | None = timedelta(seconds=3),
        worker_heartbeat_interval: timedelta | None = timedelta(seconds=10),
        reconciliation_interval: timedelta | None = timedelta(seconds=30),
        log_level: str = "low",
    ) -> Settings:
        return Settings(
            database_url,
            echo_sql,
            queue_type,
            queue_lease_timeout,
            worker_poll_interval,
            worker_heartbeat_interval,
            reconciliation_interval,
            log_level,
        )

    return factory
