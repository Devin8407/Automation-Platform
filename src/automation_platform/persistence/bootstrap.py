"""
Persistence bootstrap.

Constructs and wires together the SQLAlchemy persistence implementation
from application configuration.

This module serves as the composition root for the Persistence Layer.
"""

from typing import Callable

from ..infrastructure import Infrastructure
from .database import (
    SQLAlchemyUnitOfWorkFactory,
    UnitOfWork,
)


def build_unit_of_work_factory(infrastructure: Infrastructure) -> Callable[[], UnitOfWork]:
    """
    Build the SQLAlchemy Unit of Work factory.

    Args:
        infrastructure: SQL alchemy infrastructure.

    Returns:
        A configured SQLAlchemy Unit of Work factory.
    """

    return SQLAlchemyUnitOfWorkFactory(infrastructure.session_factory)
