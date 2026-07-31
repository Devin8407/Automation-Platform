from collections.abc import Callable

from sqlalchemy import Engine
from sqlalchemy.orm import sessionmaker

from automation_platform.config import Settings
from automation_platform.infrastructure import Infrastructure, build_infrastructure


def test_build_infrastructure(
    settings_factory: Callable[..., Settings],
) -> None:
    settings = settings_factory(database_url="sqlite:///:memory:")

    infrastructure = build_infrastructure(settings)

    assert isinstance(infrastructure, Infrastructure)
    assert isinstance(infrastructure.settings, Settings)
    assert isinstance(infrastructure.engine, Engine)
    assert isinstance(infrastructure.session_factory, sessionmaker)
