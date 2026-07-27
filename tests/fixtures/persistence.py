from collections.abc import Generator

import pytest
from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from automation_platform.persistence.database import (
    Base,
    SQLAlchemyUnitOfWorkFactory,
    UnitOfWork,
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


@pytest.fixture(scope="session")
def uow_factory(session_factory: sessionmaker[Session]) -> SQLAlchemyUnitOfWorkFactory:
    return SQLAlchemyUnitOfWorkFactory(session_factory)


@pytest.fixture
def uow(uow_factory: SQLAlchemyUnitOfWorkFactory) -> Generator[UnitOfWork, None, None]:
    with uow_factory() as uow:
        yield uow
