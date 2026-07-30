"""
Repository for workflow executions.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import case, cast, exists, select, update
from sqlalchemy.orm import Session, selectinload

from automation_platform.domain.workflow_executions import WorkflowExecution

from ...domain import TaskStatus, WorkflowStatus
from ._mapper import WorkflowExecutionMapper
from ._model import TaskExecutionModel, WorkflowExecutionModel
from .operations import (
    CompleteTaskExecutionHelperResult,
    CompleteTaskExecutionRequest,
    CompleteTaskExecutionResult,
    RetryTaskExecutionHelperResult,
    RetryTaskExecutionRequest,
    RetryTaskExecutionResult,
)


class WorkflowExecutionRepository:
    """Persists workflow executions using SQLAlchemy."""

    # ==============================================================================================
    # Constructor
    # ==============================================================================================

    def __init__(self, session: Session) -> None:
        """Initialize the repository.

        Args:
            session: SQLAlchemy session.
        """
        self._session = session

    # ==============================================================================================
    # Public API
    # ==============================================================================================

    def load(self, workflow_execution_id: UUID) -> WorkflowExecution | None:
        """Load a workflow execution.

        Args:
            workflow_execution_id: Workflow execution identifier.

        Returns:
            Loaded workflow execution if found; otherwise None.
        """

        model = self._session.scalar(
            select(WorkflowExecutionModel)
            .options(selectinload(WorkflowExecutionModel.task_executions))
            .where(WorkflowExecutionModel.id == workflow_execution_id)
        )

        if model is None:
            return None

        task_executions = [
            WorkflowExecutionMapper.task_to_domain(task_model)
            for task_model in model.task_executions
        ]

        return WorkflowExecutionMapper.workflow_to_domain(model, task_executions)

    def create(self, workflow_execution: WorkflowExecution) -> None:
        """Create a workflow execution.

        Args:
            workflow_execution: Workflow execution to create.
        """

        workflow_model = WorkflowExecutionMapper.workflow_to_model(workflow_execution)

        self._session.add(workflow_model)
        self._session.flush()

    def delete(self, workflow_execution_id: UUID) -> None:
        """Delete a workflow execution.

        Args:
            workflow_execution_id: Workflow execution identifier.
        """

        model = self._session.get(WorkflowExecutionModel, workflow_execution_id)

        if model is not None:
            self._session.delete(model)

    def find_workflow_execution(self, task_execution_id: UUID) -> UUID | None:
        """Return the owning workflow execution identifier.

        Args:
            task_execution_id: Task execution identifier.

        Returns:
            Owning workflow execution id if found; otherwise None.
        """

        return self._session.scalar(
            select(TaskExecutionModel.workflow_execution_id).where(
                TaskExecutionModel.id == task_execution_id,
            )
        )

    def start_task(self, task_execution_id: UUID, started_at: datetime) -> bool:
        """Atomically start a task execution.

        Transitions a pending task execution to the running state and records the
        time execution began. If the task execution has already been transitioned by
        another worker, no changes are made.

        Args:
            task_execution_id: Task execution identifier.
            started_at: Time the task execution started.

        Returns:
            True if the task execution was started; otherwise False.
        """

        result = self._session.execute(
            update(TaskExecutionModel)
            .where(
                TaskExecutionModel.id == task_execution_id,
                TaskExecutionModel.status == TaskStatus.PENDING,
            )
            .values(
                status=TaskStatus.RUNNING,
                started_at=started_at,
            )
        )

        return result.rowcount == 1

    def complete_task(self, request: CompleteTaskExecutionRequest) -> CompleteTaskExecutionResult:
        """Atomically complete a task execution.

        Marks the task execution as completed, releases any newly runnable child
        task executions, updates the workflow execution if all tasks have
        completed, and returns the resulting workflow state.

        Args:
            request: Necessary inputs to complete a task.

        Returns:
            Information about the completed transition, including newly runnable
            task executions and whether the workflow execution completed.
        """

        result = self._complete_task(request)

        if not result.succeeded:
            return CompleteTaskExecutionResult(
                runnable_task_execution_ids=[],
                workflow_completed=False,
            )

        runnable_task_execution_ids = self._update_child_dependencies(result.child_task_ids)

        workflow_completed = self._complete_workflow_if_finished(
            result.workflow_execution_id,
            request.completed_at,
        )

        return CompleteTaskExecutionResult(
            runnable_task_execution_ids=runnable_task_execution_ids,
            workflow_completed=workflow_completed,
        )

    def retry_task(self, request: RetryTaskExecutionRequest) -> RetryTaskExecutionResult:
        """Atomically retry a task execution.

        Attempts to retry a running task execution by decrementing its remaining retry
        count. If retries remain, the task execution is returned to the queued state.
        Otherwise, the task execution is marked as failed and the owning workflow
        execution is transitioned to the failed state.

        Args:
            request: Task retry request.

        Returns:
            Information about the retry transition, including whether the task should
            be retried and whether the workflow execution failed.
        """

        result = self._retry_task(request)

        if not result.succeeded:
            return RetryTaskExecutionResult(
                should_retry=False,
                workflow_failed=False,
            )

        workflow_failed = False

        if not result.should_retry:
            workflow_failed = self._fail_workflow(
                result.workflow_execution_id,
                request.completed_at,
            )

        return RetryTaskExecutionResult(
            should_retry=result.should_retry,
            workflow_failed=workflow_failed,
        )

    # ==============================================================================================
    # Private Helpers
    # ==============================================================================================

    def _complete_task(
        self, request: CompleteTaskExecutionRequest
    ) -> CompleteTaskExecutionHelperResult:
        """Atomically mark a task execution as completed.

        The transition only succeeds if the task execution is currently running.
        If the task has already been transitioned by another worker, no changes are
        made.

        Args:
            request: Necessary inputs to complete a task

        Returns:
            Information about the completion transition, including whether the
            transition succeeded, the workflow execution identifier, and the child
            task execution identifiers.
        """

        result = self._session.execute(
            update(TaskExecutionModel)
            .where(
                TaskExecutionModel.id == request.task_execution_id,
                TaskExecutionModel.status == TaskStatus.RUNNING,
            )
            .values(
                status=TaskStatus.COMPLETED,
                output=request.output.values,
                completed_at=request.completed_at,
            )
            .returning(TaskExecutionModel.child_task_ids, TaskExecutionModel.workflow_execution_id)
        )

        row = result.one_or_none()

        if row is None:
            return CompleteTaskExecutionHelperResult(
                succeeded=False,
                child_task_ids=[],
                workflow_execution_id=None,
            )

        return CompleteTaskExecutionHelperResult(
            succeeded=True,
            child_task_ids=row.child_task_ids,
            workflow_execution_id=row.workflow_execution_id,
        )

    def _update_child_dependencies(self, child_task_ids: list[UUID]) -> list[UUID]:
        """Release child task executions whose dependencies are now satisfied.

        Atomically decrements the remaining dependency count of each child task
        execution and returns the identifiers of those whose dependency count
        reached zero.

        Args:
            child_task_ids: ids for all child tasks.

        Returns:
            Identifiers of child task executions that became runnable.
        """

        runnable = []

        for child_id in child_task_ids:
            remaining_dependencies = self._session.execute(
                update(TaskExecutionModel)
                .where(
                    TaskExecutionModel.id == child_id,
                    TaskExecutionModel.status == TaskStatus.PENDING,
                    TaskExecutionModel.remaining_dependencies > 0,
                )
                .values(
                    remaining_dependencies=TaskExecutionModel.remaining_dependencies - 1,
                )
                .returning(TaskExecutionModel.remaining_dependencies)
            ).scalar_one_or_none()

            if remaining_dependencies == 0:
                runnable.append(child_id)

        return runnable

    def _complete_workflow_if_finished(
        self,
        workflow_execution_id: UUID,
        completed_at: datetime,
    ) -> bool:
        """Complete a workflow execution if all task executions have finished.

        Determines whether any task executions remain incomplete. If none remain,
        transitions the workflow execution to the completed state.

        Args:
            workflow_execution_id: Workflow execution identifier.
            datetime: Time the workflow's last task completed.

        Returns:
            True if the workflow execution was completed; otherwise False.
        """

        result = self._session.execute(
            update(WorkflowExecutionModel)
            .where(
                WorkflowExecutionModel.id == workflow_execution_id,
                WorkflowExecutionModel.status == WorkflowStatus.RUNNING,
                ~exists(
                    select(1).where(
                        TaskExecutionModel.workflow_execution_id == workflow_execution_id,
                        TaskExecutionModel.status != TaskStatus.COMPLETED,
                    )
                ),
            )
            .values(
                status=WorkflowStatus.COMPLETED,
                completed_at=completed_at,
            )
        )

        return result.rowcount == 1

    def _retry_task(self, request: RetryTaskExecutionRequest) -> RetryTaskExecutionHelperResult:
        """Atomically retry a task execution.

        Decrements the remaining retry count of a running task execution. If retries
        remain, the task execution is returned to the queued state. Otherwise, the
        task execution is marked as failed. If the task has already been transitioned
        by another worker, no changes are made.

        Args:
            request: Task retry request.

        Returns:
            Information about the retry transition, including whether the update
            succeeded, whether retries remain, and the owning workflow execution.
        """

        row = self._session.execute(
            update(TaskExecutionModel)
            .where(
                TaskExecutionModel.id == request.task_execution_id,
                TaskExecutionModel.status == TaskStatus.RUNNING,
                TaskExecutionModel.remaining_tries > 0,
            )
            .values(
                remaining_tries=TaskExecutionModel.remaining_tries - 1,
                status=cast(
                    case(
                        (
                            TaskExecutionModel.remaining_tries > 1,
                            TaskStatus.PENDING,
                        ),
                        else_=TaskStatus.FAILED,
                    ),
                    TaskExecutionModel.status.type,
                ),
                error_message=request.error_message,
                completed_at=case(
                    (
                        TaskExecutionModel.remaining_tries > 1,
                        None,
                    ),
                    else_=request.completed_at,
                ),
            )
            .returning(
                TaskExecutionModel.remaining_tries,
                TaskExecutionModel.workflow_execution_id,
            )
        ).one_or_none()

        if row is None:
            return RetryTaskExecutionHelperResult(
                succeeded=False,
                should_retry=False,
                workflow_execution_id=None,
            )

        return RetryTaskExecutionHelperResult(
            succeeded=True,
            should_retry=row.remaining_tries > 0,
            workflow_execution_id=row.workflow_execution_id,
        )

    def _fail_workflow(self, workflow_execution_id: UUID, completed_at: datetime) -> bool:
        """Atomically fail a workflow execution.

        Transitions a running workflow execution to the failed state. If the workflow
        execution has already been transitioned, no changes are made.

        Args:
            workflow_execution_id: Workflow execution identifier.
            completed_at: Time the workflow execution completed.

        Returns:
            True if the workflow execution was failed; otherwise False.
        """

        result = self._session.execute(
            update(WorkflowExecutionModel)
            .where(
                WorkflowExecutionModel.id == workflow_execution_id,
                WorkflowExecutionModel.status == WorkflowStatus.RUNNING,
            )
            .values(
                status=WorkflowStatus.FAILED,
                completed_at=completed_at,
            )
        )

        return result.rowcount == 1
