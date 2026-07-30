"""
SQLAlchemy models for workflow executions.

These models define how workflow executions are persisted within
PostgreSQL. They are internal to the Persistence Layer and should
never be exposed outside of it.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ...domain.common.enums import TaskStatus, WorkflowStatus
from ..database import Base


class WorkflowExecutionModel(Base):
    """Persisted workflow execution."""

    __tablename__ = "workflow_executions"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)

    workflow_definition_id: Mapped[UUID] = mapped_column(
        ForeignKey("workflow_definitions.id"),
        nullable=False,
        index=True,
    )

    status: Mapped[WorkflowStatus] = mapped_column(Enum(WorkflowStatus), nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    task_executions: Mapped[list[TaskExecutionModel]] = relationship(
        back_populates="workflow_execution",
        cascade="all, delete-orphan",
    )


class TaskExecutionModel(Base):
    """Persisted task execution."""

    __tablename__ = "task_executions"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)

    workflow_execution_id: Mapped[UUID] = mapped_column(
        ForeignKey("workflow_executions.id"),
        nullable=False,
        index=True,
    )
    task_definition_id: Mapped[UUID] = mapped_column(
        ForeignKey("task_definitions.id"),
        nullable=False,
        index=True,
    )

    status: Mapped[TaskStatus] = mapped_column(Enum(TaskStatus), nullable=False)

    remaining_dependencies: Mapped[int] = mapped_column(Integer, nullable=False)

    parent_task_ids: Mapped[list[UUID]] = mapped_column(
        ARRAY(PG_UUID(as_uuid=True)),
        nullable=False,
    )
    child_task_ids: Mapped[list[UUID]] = mapped_column(
        ARRAY(PG_UUID(as_uuid=True)),
        nullable=False,
    )

    remaining_tries: Mapped[int] = mapped_column(Integer, nullable=False)

    output: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    error_message: Mapped[str | None] = mapped_column(String)

    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    workflow_execution: Mapped[WorkflowExecutionModel] = relationship(
        back_populates="task_executions",
    )
