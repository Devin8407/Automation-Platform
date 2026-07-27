"""
Repository for workflow executions.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from automation_platform.domain.workflow_executions import WorkflowExecution

from ._mapper import WorkflowExecutionMapper
from ._model import TaskExecutionModel, WorkflowExecutionModel


class WorkflowExecutionRepository:
    """Persists workflow executions using SQLAlchemy."""

    def __init__(self, session: Session) -> None:
        """Initialize the repository.

        Args:
            session: SQLAlchemy session.
        """
        self._session = session

    def load(self, workflow_execution_id: UUID) -> WorkflowExecution | None:
        """Load a workflow execution.

        Args:
            workflow_execution_id: Workflow execution identifier.

        Returns:
            Loaded workflow execution if found; otherwise None.
        """

        model = self._session.get(WorkflowExecutionModel, workflow_execution_id)

        if model is None:
            return None

        task_executions = [
            WorkflowExecutionMapper.task_to_domain(task_model)
            for task_model in model.task_executions
        ]

        return WorkflowExecutionMapper.workflow_to_domain(model, task_executions)

    def save(self, workflow_execution: WorkflowExecution) -> None:
        """Persist a workflow execution.

        Args:
            workflow_execution: Workflow execution to persist.
        """

        workflow_model = WorkflowExecutionMapper.workflow_to_model(workflow_execution)

        self._session.merge(workflow_model)

    def delete(self, workflow_execution_id: UUID) -> None:
        """Delete a workflow execution.

        Args:
            workflow_execution_id: Workflow execution identifier.
        """

        model = self._session.get(WorkflowExecutionModel, workflow_execution_id)

        if model is not None:
            self._session.delete(model)

    def find_workflow_execution(self, task_execution_id: UUID) -> UUID | None:
        """Return the owning workflow execution identifier."""

        return self._session.scalar(
            select(TaskExecutionModel.workflow_execution_id).where(
                TaskExecutionModel.id == task_execution_id,
            )
        )
