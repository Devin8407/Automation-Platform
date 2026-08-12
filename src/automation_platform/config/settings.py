from dataclasses import dataclass
from datetime import timedelta


@dataclass(frozen=True)
class Settings:
    database_url: str
    echo_sql: bool

    queue_type: str
    queue_lease_timeout: timedelta

    worker_poll_interval: timedelta
    worker_heartbeat_interval: timedelta

    scheduler_poll_interval: timedelta

    reconciliation_interval: timedelta

    api_host: str
    api_port: str

    log_level: str
