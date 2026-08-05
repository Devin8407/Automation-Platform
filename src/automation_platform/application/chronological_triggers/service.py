"""Application service for chronological trigger scheduling."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone

from ...domain import TriggerDefinition
from ...persistence import UnitOfWork
from ...plugins.triggers import ChronologicalTrigger, TriggerRegistry
from ..workflow_start import WorkflowStartService


class ChronologicalTriggerService:
    """Coordinates initialization and processing of chronological triggers."""

    # ==============================================================================================
    # Constructor
    # ==============================================================================================

    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        trigger_registry: TriggerRegistry,
        workflow_start_service: WorkflowStartService,
    ) -> None:
        """Initialize the chronological trigger service.

        Args:
            uow_factory: Factory for creating persistence units of work.
            trigger_registry: Registry used to resolve trigger plugins.
            workflow_start_service: Service used to start workflow executions.
        """

        self._uow_factory = uow_factory
        self._trigger_registry = trigger_registry
        self._workflow_start_service = workflow_start_service

    # ==============================================================================================
    # Public API
    # ==============================================================================================

    def initialize(
        self,
        trigger_plugin: type[ChronologicalTrigger],
        trigger_definition: TriggerDefinition,
        uow: UnitOfWork,
    ) -> None:
        """Initialize durable scheduling state for a chronological trigger.

        Calculates the trigger's first occurrence and persists its scheduling
        state using the caller's unit of work. The caller remains responsible
        for committing the transaction.

        Args:
            trigger_plugin: Resolved chronological trigger implementation.
            trigger_definition: Trigger definition being initialized.
            uow: Existing unit of work for definition creation.
        """

        next_run_at = trigger_plugin.next_occurrence(
            trigger_definition.configuration,
            datetime.now(timezone.utc),
        )

        if next_run_at is None:
            return

        uow.chronological_triggers.create(
            trigger_definition.id,
            next_run_at,
        )

    def process_next_due(self) -> bool:
        """Process the earliest currently due chronological trigger.

        Claims one due occurrence through persistence, calculates and persists
        its next occurrence, and starts the associated workflow in the same
        transaction.

        Returns:
            True if a due occurrence was processed; otherwise False.
        """

        now = datetime.now(timezone.utc)

        with self._uow_factory() as uow:
            due_trigger = uow.chronological_triggers.get_next_due(now)

            if due_trigger is None:
                return False

            trigger_plugin: ChronologicalTrigger = self._trigger_registry.get(
                due_trigger.plugin_type
            )

            next_run_at = trigger_plugin.next_occurrence(
                due_trigger.configuration,
                due_trigger.next_run_at,
            )

            if next_run_at is None:
                uow.chronological_triggers.delete(due_trigger.trigger_definition_id)
            else:
                uow.chronological_triggers.update_next_run(
                    due_trigger.trigger_definition_id,
                    next_run_at,
                )

            self._workflow_start_service.start_and_commit(
                due_trigger.workflow_definition_id,
                uow,
            )

        return True
