from dataclasses import dataclass
from datetime import timedelta


@dataclass(frozen=True)
class Settings:
    database_url: str
    echo_sql: bool

    queue_type: str
    queue_lease_timeout: timedelta

    worker_count: int

    log_level: str
