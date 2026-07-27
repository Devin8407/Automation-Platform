from automation_platform.config import Settings
from automation_platform.persistence import build_unit_of_work_factory
from automation_platform.persistence.database import SQLAlchemyUnitOfWorkFactory


def test_build_unit_of_work_factory_returns_factory() -> None:
    settings = Settings(
        database_url="sqlite:///:memory:",
        echo_sql=False,
        worker_count=1,
        queue_poll_interval=1.0,
        log_level="Low",
    )

    factory = build_unit_of_work_factory(settings)

    assert isinstance(factory, SQLAlchemyUnitOfWorkFactory)
