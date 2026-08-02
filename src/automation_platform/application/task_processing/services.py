"""Application service for processing task executions."""

from collections.abc import Callable
from datetime import datetime, timezone
from uuid import UUID

from ...domain import TaskContext, TaskOutput
from ...persistence import (
    CompleteTaskExecutionRequest,
    RetryTaskExecutionRequest,
    StartTaskExecutionResult,
    UnitOfWork,
)
from ...plugins import TaskRegistry
from .models import ProcessTaskResult


class TaskProcessingService:
    """Orchestrates the processing of individual task executions."""

    # ==============================================================================================
    # Constructor
    # ==============================================================================================

    def __init__(
        self,
        uow_factory: Callable[..., UnitOfWork],
        task_registry: TaskRegistry,
    ) -> None:
        """Initialize the task processing service.

        Args:
            uow_factory: Factory used to create units of work.
            task_registry: Registry used to resolve task plugin implementations.
        """

        self._uow_factory = uow_factory
        self._task_registry = task_registry

    # ==============================================================================================
    # Public API
    # ==============================================================================================

    def process(self, task_execution_id: UUID) -> ProcessTaskResult:
        """Process a task execution.

        Starts or resumes the task execution, executes its registered plugin
        outside of a persistence transaction, and persists the resulting
        success or failure.

        Args:
            task_execution_id: Identifier of the task execution to process.

        Returns:
            Task execution identifiers that should be
            enqueued after processing.
        """

        task = self._start_task(task_execution_id)

        if task is None:
            return ProcessTaskResult()

        plugin_type = self._task_registry.get(task.plugin_type)
        plugin = plugin_type()

        context = TaskContext(
            configuration=task.configuration,
            inputs=task.parent_outputs,
        )

        result = plugin.execute(context)

        if result.succeeded:
            return self._complete_task(
                task_execution_id,
                result.output,
            )

        return self._retry_task(
            task_execution_id,
            result.message,
        )

    # ==============================================================================================
    # Private Helpers
    # ==============================================================================================

    def _start_task(
        self,
        task_execution_id: UUID,
    ) -> StartTaskExecutionResult | None:
        """Start or resume a task execution.

        The running state is committed before plugin execution so that no
        database transaction remains open while arbitrary plugin work is
        performed.

        Args:
            task_execution_id: Identifier of the task execution to process.

        Returns:
            Execution data required by the task plugin if the task is
            processable; otherwise None.
        """

        with self._uow_factory() as uow:
            result = uow.workflow_executions.start_task(
                task_execution_id,
                datetime.now(timezone.utc),
            )

            if result is None:
                return None

            uow.commit()

        return result

    def _complete_task(
        self,
        task_execution_id: UUID,
        output: TaskOutput,
    ) -> ProcessTaskResult:
        """Persist successful completion of a task execution.

        Args:
            task_execution_id: Identifier of the completed task execution.
            output: Output produced by the task plugin.

        Returns:
            Result containing any newly runnable child task executions.
        """

        with self._uow_factory() as uow:
            result = uow.workflow_executions.complete_task(
                CompleteTaskExecutionRequest(
                    task_execution_id=task_execution_id,
                    output=output,
                    completed_at=datetime.now(timezone.utc),
                )
            )
            uow.commit()

        return ProcessTaskResult(enqueue_task_ids=result.runnable_task_execution_ids)

    def _retry_task(
        self,
        task_execution_id: UUID,
        error_message: str | None,
    ) -> ProcessTaskResult:
        """Persist a failed task execution attempt.

        If another try remains, the task execution is returned for
        re-enqueueing. Otherwise persistence terminally fails the task and
        its workflow.

        Args:
            task_execution_id: Identifier of the failed task execution.
            error_message: Failure message reported by the task plugin.

        Returns:
            Result containing the current task execution identifier when
            another attempt should be enqueued; otherwise an empty result.
        """

        with self._uow_factory() as uow:
            result = uow.workflow_executions.retry_task(
                RetryTaskExecutionRequest(
                    task_execution_id=task_execution_id,
                    error_message=error_message,
                    completed_at=datetime.now(timezone.utc),
                )
            )
            uow.commit()

        return ProcessTaskResult(should_retry=result.should_retry)
