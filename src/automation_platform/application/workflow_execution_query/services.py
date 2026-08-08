"""Application service for retrieving workflow execution state."""

from __future__ import annotations

from collections.abc import Callable
from uuid import UUID

from ...domain import WorkflowExecution
from ...persistence import UnitOfWork
from ..exceptions import WorkflowExecutionNotFoundError


class WorkflowExecutionQueryService:
    """Provides read access to workflow execution state."""

    # ==============================================================================================
    # Constructor
    # ==============================================================================================

    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
    ) -> None:
        """Initialize the workflow execution query service.

        Args:
            uow_factory: Factory for creating persistence units of work.
        """

        self._uow_factory = uow_factory

    # ==============================================================================================
    # Public API
    # ==============================================================================================

    def get(self, workflow_execution_id: UUID) -> WorkflowExecution:
        """Retrieve a workflow execution.

        Args:
            workflow_execution_id: Identifier of the workflow execution.

        Returns:
            The requested workflow execution.

        Raises:
            WorkflowExecutionNotFoundError: If the workflow execution does not exist.
        """

        with self._uow_factory() as uow:
            workflow_execution = uow.workflow_executions.load(
                workflow_execution_id,
            )

        if workflow_execution is None:
            raise WorkflowExecutionNotFoundError(
                f"Workflow execution {workflow_execution_id} does not exist."
            )

        return workflow_execution
