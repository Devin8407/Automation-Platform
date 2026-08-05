"""
Repository for chronological trigger state.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from automation_platform.persistence.workflow_definitions._model import (
    TriggerDefinitionModel,
)

from ._model import ChronologicalTriggerStateModel
from .operations import DueChronologicalTrigger


class ChronologicalTriggerRepository:
    """Persists chronological trigger scheduling state using SQLAlchemy."""

    def __init__(self, session: Session) -> None:
        """Initialize the repository.

        Args:
            session: SQLAlchemy session.
        """

        self._session = session

    def create(
        self,
        trigger_definition_id: UUID,
        next_run_at: datetime,
    ) -> None:
        """Create scheduling state for a chronological trigger.

        Args:
            trigger_definition_id: ID of the associated trigger definition.
            next_run_at: First scheduled occurrence.
        """

        state = ChronologicalTriggerStateModel(
            trigger_definition_id=trigger_definition_id,
            next_run_at=next_run_at,
        )

        self._session.add(state)

    def delete(
        self,
        trigger_definition_id: UUID,
    ) -> None:
        """Delete scheduling state for a chronological trigger.

        If no scheduling state exists for the trigger definition, the operation
        completes without making any changes.

        Args:
            trigger_definition_id: ID of the associated trigger definition.
        """

        state = self._session.get(
            ChronologicalTriggerStateModel,
            trigger_definition_id,
        )

        if state is not None:
            self._session.delete(state)

    def get_next_due(
        self,
        now: datetime,
    ) -> DueChronologicalTrigger | None:
        """Get and lock the earliest due chronological trigger.

        Locked rows are skipped so concurrent schedulers can process
        different triggers without blocking one another.

        Args:
            now: Time at which trigger readiness is evaluated.

        Returns:
            The earliest due chronological trigger, or None if no trigger
            is currently due.
        """

        statement = (
            select(
                ChronologicalTriggerStateModel,
                TriggerDefinitionModel,
            )
            .join(
                TriggerDefinitionModel,
                TriggerDefinitionModel.id == ChronologicalTriggerStateModel.trigger_definition_id,
            )
            .where(
                ChronologicalTriggerStateModel.next_run_at <= now,
                TriggerDefinitionModel.enabled.is_(True),
            )
            .order_by(
                ChronologicalTriggerStateModel.next_run_at,
                ChronologicalTriggerStateModel.trigger_definition_id,
            )
            .with_for_update(
                skip_locked=True,
                of=ChronologicalTriggerStateModel,
            )
            .limit(1)
        )

        result = self._session.execute(statement).first()

        if result is None:
            return None

        state, trigger_definition = result

        return DueChronologicalTrigger(
            trigger_definition_id=state.trigger_definition_id,
            workflow_definition_id=trigger_definition.workflow_definition_id,
            plugin_type=trigger_definition.plugin_type,
            configuration=trigger_definition.configuration,
            next_run_at=state.next_run_at,
        )

    def update_next_run(
        self,
        trigger_definition_id: UUID,
        next_run_at: datetime,
    ) -> None:
        """Update the next scheduled occurrence for a trigger.

        Args:
            trigger_definition_id: ID of the trigger definition.
            next_run_at: Newly calculated next occurrence.
        """

        state = self._session.get(
            ChronologicalTriggerStateModel,
            trigger_definition_id,
        )

        if state is None:
            raise ValueError(
                "Chronological trigger state does not exist for "
                f"trigger definition {trigger_definition_id}."
            )

        state.next_run_at = next_run_at
