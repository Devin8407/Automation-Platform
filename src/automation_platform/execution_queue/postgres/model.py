"""SQLAlchemy model representing a queue entry."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    DateTime,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from ...infrastructure import Base


class QueueEntryModel(Base):
    """Represents a runnable task execution stored in the PostgreSQL queue.

    Each row corresponds to a single task execution awaiting processing or
    currently leased by a worker. Queue metadata such as lease ownership and
    heartbeat timestamps are maintained independently from workflow execution
    state.
    """

    __tablename__ = "execution_queue"

    task_execution_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    claim_token: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True))

    claimed_by: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), index=True)

    queued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_heartbeat: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
