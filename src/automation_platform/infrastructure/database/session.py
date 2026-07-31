"""
Creates SQLAlchemy Session factories.

A SessionFactory creates new SQLAlchemy Sessions that share the same
Engine and connection pool.

Each Unit of Work creates a fresh Session from this factory.
"""

from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    """
    Create a SQLAlchemy Session factory.

    Args:
        engine: SQLAlchemy Engine used to create Sessions.

    Returns:
        A configured SQLAlchemy Session factory.
    """

    return sessionmaker(
        bind=engine,
        expire_on_commit=False,
    )
