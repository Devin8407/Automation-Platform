from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    database_url: str
    echo_sql: bool

    worker_count: int
    queue_poll_interval: float

    log_level: str
