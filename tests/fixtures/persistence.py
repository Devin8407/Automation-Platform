from collections.abc import Generator

import pytest
from sqlalchemy.orm import Session, sessionmaker

from automation_platform.persistence.database import (
    SQLAlchemyUnitOfWorkFactory,
    UnitOfWork,
)


@pytest.fixture(scope="session")
def uow_factory(session_factory: sessionmaker[Session]) -> SQLAlchemyUnitOfWorkFactory:
    return SQLAlchemyUnitOfWorkFactory(session_factory)


@pytest.fixture
def uow(uow_factory: SQLAlchemyUnitOfWorkFactory) -> Generator[UnitOfWork, None, None]:
    with uow_factory() as uow:
        yield uow
