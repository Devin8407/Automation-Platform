from collections.abc import Callable, Generator

import pytest
from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from automation_platform.config import Settings
from automation_platform.infrastructure import Infrastructure
from automation_platform.infrastructure.database import (
    Base,
    create_session_factory,
    create_sqlalchemy_engine,
)

TEST_DATABASE_URL = "postgresql+psycopg://automation:password@localhost:5432/automation_test"


@pytest.fixture(scope="session")
def engine() -> Generator[Engine, None, None]:
    engine = create_sqlalchemy_engine(TEST_DATABASE_URL, echo_sql=False)

    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

    yield engine

    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture(scope="session")
def session_factory(engine: Engine) -> sessionmaker[Session]:
    return create_session_factory(engine)


@pytest.fixture
def session(session_factory: sessionmaker[Session]) -> Generator[Session, None, None]:
    session = session_factory()

    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def infrastructure_factory(
    settings_factory: Callable[..., Settings],
    engine: Engine,
    session_factory: sessionmaker,
) -> Callable[..., Infrastructure]:
    """Create infrastructure for tests."""

    def factory(
        *,
        settings: Settings = settings_factory(),
        engine: Engine = engine,
        session_factory: sessionmaker = session_factory,
    ) -> Infrastructure:
        return Infrastructure(
            settings,
            engine,
            session_factory,
        )

    return factory
