"""
Maps workflow execution domain objects to SQLAlchemy models and back.

Repositories use these helpers to translate between the domain model and the
Persistence Layer. Mappers contain no database logic and perform no queries.
"""

from __future__ import annotations

from automation_platform.domain.workflow_executions import (
    TaskExecution,
    WorkflowExecution,
)

from ...domain import TaskOutput
from ._model import (
    TaskExecutionModel,
    WorkflowExecutionModel,
)


class WorkflowExecutionMapper:
    """Converts workflow execution domain objects and SQLAlchemy models."""

    @staticmethod
    def workflow_to_model(workflow: WorkflowExecution) -> WorkflowExecutionModel:
        """Convert a workflow execution into its SQLAlchemy model.

        Args:
            workflow: Domain workflow execution.

        Returns:
            SQLAlchemy workflow execution model.
        """
        model = WorkflowExecutionModel(
            id=workflow.id,
            workflow_definition_id=workflow.workflow_definition_id,
            status=workflow.status,
            remaining_tasks=workflow.remaining_tasks,
            created_at=workflow.created_at,
            started_at=workflow.started_at,
            completed_at=workflow.completed_at,
        )

        model.task_executions = [
            WorkflowExecutionMapper.task_to_model(task) for task in workflow.task_executions
        ]

        return model

    @staticmethod
    def workflow_to_domain(
        model: WorkflowExecutionModel,
        task_executions: list[TaskExecution],
    ) -> WorkflowExecution:
        """Convert a workflow execution model into a domain object.

        Args:
            model: SQLAlchemy workflow execution model.
            task_executions: Domain task executions belonging to the workflow.

        Returns:
            Domain workflow execution.
        """
        return WorkflowExecution(
            id=model.id,
            workflow_definition_id=model.workflow_definition_id,
            status=model.status,
            task_executions=task_executions,
            created_at=model.created_at,
            started_at=model.started_at,
            completed_at=model.completed_at,
            remaining_tasks=model.remaining_tasks,
        )

    @staticmethod
    def task_to_model(task: TaskExecution) -> TaskExecutionModel:
        """Convert a task execution into its SQLAlchemy model.

        Args:
            workflow_execution_id: Owning workflow execution identifier.
            task: Domain task execution.

        Returns:
            SQLAlchemy task execution model.
        """
        return TaskExecutionModel(
            id=task.id,
            workflow_execution_id=task.workflow_execution_id,
            task_definition_id=task.task_definition_id,
            status=task.status,
            remaining_dependencies=task.remaining_dependencies,
            child_task_ids=task.child_task_ids,
            retry_count=task.retry_count,
            output=(None if task.output is None else task.output.values),
            error_message=task.error_message,
            started_at=task.started_at,
            completed_at=task.completed_at,
        )

    @staticmethod
    def task_to_domain(model: TaskExecutionModel) -> TaskExecution:
        """Convert a task execution model into a domain object.

        Args:
            model: SQLAlchemy task execution model.

        Returns:
            Domain task execution.
        """
        return TaskExecution(
            id=model.id,
            workflow_execution_id=model.workflow_execution_id,
            task_definition_id=model.task_definition_id,
            status=model.status,
            remaining_dependencies=model.remaining_dependencies,
            child_task_ids=model.child_task_ids,
            retry_count=model.retry_count,
            output=(None if model.output is None else TaskOutput(values=model.output)),
            error_message=model.error_message,
            started_at=model.started_at,
            completed_at=model.completed_at,
        )
