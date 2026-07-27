"""
SQLAlchemy implementation of the Unit of Work.

Each Unit of Work owns a single SQLAlchemy Session and constructs
repositories that participate in the same database transaction.
"""

from __future__ import annotations

from types import TracebackType
from typing import Self

from sqlalchemy.orm import Session, sessionmaker

from ..workflow_definitions.repository import WorkflowDefinitionRepository
from ..workflow_executions.repository import WorkflowExecutionRepository
from .unit_of_work import UnitOfWork


class SQLAlchemyUnitOfWork(UnitOfWork):
    """
    SQLAlchemy implementation of the Unit of Work pattern.
    """

    def __init__(self, session: Session) -> None:
        self._session = session

        self.workflow_definitions = WorkflowDefinitionRepository(session)
        self.workflow_executions = WorkflowExecutionRepository(session)

    def commit(self) -> None:
        """Commit the current transaction."""

        self._session.commit()

    def rollback(self) -> None:
        """Roll back the current transaction."""

        self._session.rollback()

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if exc_type is not None:
            self.rollback()

        self._session.close()


class SQLAlchemyUnitOfWorkFactory:
    """Creates SQLAlchemy Unit of Work instances."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def __call__(self) -> SQLAlchemyUnitOfWork:
        session = self._session_factory()

        return SQLAlchemyUnitOfWork(session)
