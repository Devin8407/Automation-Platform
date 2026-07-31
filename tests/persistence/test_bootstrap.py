from collections.abc import Callable

from automation_platform.config import Settings
from automation_platform.infrastructure import Infrastructure
from automation_platform.persistence import build_unit_of_work_factory
from automation_platform.persistence.database import SQLAlchemyUnitOfWorkFactory


def test_build_unit_of_work_factory_returns_factory(
    settings_factory: Callable[..., Settings],
    infrastructure_factory: Callable[..., Infrastructure],
) -> None:
    settings = settings_factory(database_url="sqlite:///:memory:")

    infrastructure = infrastructure_factory(settings=settings)

    factory = build_unit_of_work_factory(infrastructure)

    assert isinstance(factory, SQLAlchemyUnitOfWorkFactory)
