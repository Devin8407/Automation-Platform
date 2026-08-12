"""Persistence model for chronological trigger state."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from ...infrastructure import Base


class ChronologicalTriggerStateModel(Base):
    """Persisted scheduling state for a chronological trigger."""

    __tablename__ = "chronological_trigger_state"

    trigger_definition_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("trigger_definitions.id", ondelete="CASCADE"),
        primary_key=True,
    )

    next_run_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
