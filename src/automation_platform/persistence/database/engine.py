"""
Database Engine.

Provides construction of SQLAlchemy Engine instances used by the
Persistence Layer.

The Engine owns the connection pool for a runtime process and is
created once during process initialization.
"""

from sqlalchemy import Engine, create_engine


def create_sqlalchemy_engine(database_url: str, echo_sql: bool) -> Engine:
    """
    Create a SQLAlchemy Engine.

    Args:
        database_url: SQLAlchemy database connection URL.
        echo_sql: Whether SQLAlchemy should log all SQL statements.

    Returns:
        A configured SQLAlchemy Engine.
    """

    return create_engine(
        database_url,
        echo=echo_sql,
        pool_pre_ping=True,
    )
