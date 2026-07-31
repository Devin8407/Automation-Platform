"""
SQLAlchemy models for workflow definitions.

These models define how workflow definitions are persisted within
PostgreSQL. They are internal to the Persistence Layer and should
never be exposed outside of it.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import (
    Boolean,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ...infrastructure import Base


class WorkflowDefinitionModel(Base):
    """Persisted workflow definition."""

    __tablename__ = "workflow_definitions"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False)

    task_definitions: Mapped[list[TaskDefinitionModel]] = relationship(
        back_populates="workflow_definition",
        cascade="all, delete-orphan",
    )
    trigger_definitions: Mapped[list[TriggerDefinitionModel]] = relationship(
        back_populates="workflow_definition",
        cascade="all, delete-orphan",
    )


class TaskDefinitionModel(Base):
    """Persisted task definition."""

    __tablename__ = "task_definitions"

    __table_args__ = (
        UniqueConstraint(
            "workflow_definition_id",
            "key",
            name="uq_task_definition_workflow_key",
        ),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    workflow_definition_id: Mapped[UUID] = mapped_column(
        ForeignKey("workflow_definitions.id"),
        nullable=False,
        index=True,
    )
    key: Mapped[str] = mapped_column(String, nullable=False)
    plugin_type: Mapped[str] = mapped_column(String, nullable=False)
    configuration: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    max_retries: Mapped[int] = mapped_column(Integer, nullable=False)
    workflow_definition: Mapped[WorkflowDefinitionModel] = relationship(
        back_populates="task_definitions",
    )


class TaskDefinitionDependencyModel(Base):
    """Persisted dependency edge between task definitions."""

    __tablename__ = "task_definition_dependencies"

    task_definition_id: Mapped[UUID] = mapped_column(
        ForeignKey("task_definitions.id"),
        primary_key=True,
    )
    depends_on_task_definition_id: Mapped[UUID] = mapped_column(
        ForeignKey("task_definitions.id"),
        primary_key=True,
    )


class TriggerDefinitionModel(Base):
    """Persisted trigger definition."""

    __tablename__ = "trigger_definitions"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    workflow_definition_id: Mapped[UUID] = mapped_column(
        ForeignKey("workflow_definitions.id"),
        nullable=False,
        index=True,
    )
    plugin_type: Mapped[str] = mapped_column(String, nullable=False)
    configuration: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False)

    workflow_definition: Mapped["WorkflowDefinitionModel"] = relationship(
        back_populates="trigger_definitions",
    )
