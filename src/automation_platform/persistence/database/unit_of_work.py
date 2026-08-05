from __future__ import annotations

from types import TracebackType
from typing import Protocol, Self

from ..chronological_triggers import ChronologicalTriggerRepository
from ..workflow_definitions.repository import WorkflowDefinitionRepository
from ..workflow_executions.repository import WorkflowExecutionRepository


class UnitOfWork(Protocol):
    """
    Coordinates repositories participating in a single database transaction.
    """

    chronological_triggers: ChronologicalTriggerRepository
    workflow_definitions: WorkflowDefinitionRepository
    workflow_executions: WorkflowExecutionRepository

    def commit(self) -> None: ...

    def rollback(self) -> None: ...

    def __enter__(self) -> Self: ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None: ...
