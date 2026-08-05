"""Application Service for dispatching trigger initialization by trigger mechanism."""

from __future__ import annotations

from ...domain import TriggerDefinition
from ...persistence import UnitOfWork
from ...plugins import Trigger
from ...plugins.triggers import ChronologicalTrigger
from ..chronological_triggers import ChronologicalTriggerService


class TriggerInitializationService:
    """Dispatches trigger initialization by trigger mechanism."""

    def __init__(
        self,
        chronological_trigger_service: ChronologicalTriggerService,
    ) -> None:
        self._initializers = {
            ChronologicalTrigger: chronological_trigger_service.initialize,
        }

    def initialize(
        self,
        trigger_plugin: type[Trigger],
        trigger_definition: TriggerDefinition,
        uow: UnitOfWork,
    ) -> None:
        """Initialize mechanism-specific state for a trigger definition."""

        for mechanism, initializer in self._initializers.items():
            if issubclass(trigger_plugin, mechanism):
                initializer(
                    trigger_plugin,
                    trigger_definition,
                    uow,
                )
                return
