"""
Persistence bootstrap.

Constructs and wires together the SQLAlchemy persistence implementation
from application configuration.

This module serves as the composition root for the Persistence Layer.
"""

from typing import Callable

from ..config import Settings
from .database import (
    SQLAlchemyUnitOfWorkFactory,
    UnitOfWork,
    create_session_factory,
    create_sqlalchemy_engine,
)


def build_unit_of_work_factory(settings: Settings) -> Callable[[], UnitOfWork]:
    """
    Build the SQLAlchemy Unit of Work factory.

    Args:
        settings: Application configuration.

    Returns:
        A configured SQLAlchemy Unit of Work factory.
    """

    engine = create_sqlalchemy_engine(settings.database_url, settings.echo_sql)

    session_factory = create_session_factory(engine)

    return SQLAlchemyUnitOfWorkFactory(session_factory)
