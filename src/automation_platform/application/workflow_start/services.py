"""Application service for starting workflow executions."""

from collections.abc import Callable
from uuid import UUID, uuid4

from ...domain import (
    TaskDefinition,
    TaskExecution,
    TaskStatus,
    WorkflowDefinition,
    WorkflowExecution,
    WorkflowStatus,
)
from ...execution_queue import ExecutionQueue
from ...persistence import UnitOfWork
from ..exceptions import (
    WorkflowDefinitionDisabledError,
    WorkflowDefinitionNotFoundError,
)


class WorkflowStartService:
    """Coordinates creation and initial scheduling of workflow executions."""

    # ==============================================================================================
    # Constructor
    # ==============================================================================================

    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        execution_queue: ExecutionQueue,
    ) -> None:
        """Initialize the workflow start service.

        Args:
            uow_factory: Factory for creating persistence units of work.
            queue: Execution queue used to enqueue runnable tasks.
        """

        self._uow_factory = uow_factory
        self._execution_queue = execution_queue

    # ==============================================================================================
    # Public API
    # ==============================================================================================

    def start(self, workflow_definition_id: UUID) -> UUID:
        """Create and start an execution of a workflow definition.

        Loads the requested workflow definition, creates its workflow and task
        execution state, persists the execution atomically, and enqueues the
        initially runnable tasks after the transaction commits.

        Args:
            workflow_definition_id: Identifier of the workflow definition to start.

        Returns:
            Identifier of the created workflow execution.

        Raises:
            WorkflowDefinitionNotFoundError: If the workflow definition does not exist.
            WorkflowDefinitionDisabledError: If the workflow definition is disabled.
        """

        with self._uow_factory() as uow:
            workflow_definition = uow.workflow_definitions.load(workflow_definition_id)

            if workflow_definition is None:
                raise WorkflowDefinitionNotFoundError(
                    f"Workflow definition {workflow_definition_id} does not exist."
                )

            if not workflow_definition.enabled:
                raise WorkflowDefinitionDisabledError(
                    f"Workflow definition {workflow_definition_id} is disabled."
                )

            workflow_execution, root_task_ids = self._create_workflow_execution(workflow_definition)

            uow.workflow_executions.create(workflow_execution)
            uow.commit()

        self._execution_queue.enqueue(root_task_ids)

        return workflow_execution.id

    # ==============================================================================================
    # Private Helpers
    # ==============================================================================================

    def _create_workflow_execution(
        self,
        workflow_definition: WorkflowDefinition,
    ) -> tuple[WorkflowExecution, list[UUID]]:
        """Create runtime execution state from a workflow definition.

        Creates a new task execution for every task definition and translates
        definition dependency relationships into execution parent and child
        relationships.

        Args:
            workflow_definition: Workflow definition being executed.

        Returns:
            Newly created workflow execution and its root tasks.
        """

        workflow_execution_id = uuid4()

        task_execution_ids = {
            task_definition.id: uuid4() for task_definition in workflow_definition.task_definitions
        }

        child_task_ids = self._create_child_task_lookup(
            workflow_definition.task_definitions,
            task_execution_ids,
        )

        root_task_ids = []
        task_executions = []

        for task_definition in workflow_definition.task_definitions:
            task_execution = TaskExecution(
                id=task_execution_ids[task_definition.id],
                workflow_execution_id=workflow_execution_id,
                key=task_definition.key,
                plugin_type=task_definition.plugin_type,
                configuration=task_definition.configuration,
                task_definition_id=task_definition.id,
                status=TaskStatus.PENDING,
                remaining_dependencies=len(task_definition.dependencies),
                remaining_tries=task_definition.max_tries,
                parent_task_ids=[
                    task_execution_ids[parent_id] for parent_id in task_definition.dependencies
                ],
                child_task_ids=child_task_ids[task_definition.id],
            )

            task_executions.append(task_execution)

            if task_execution.remaining_dependencies == 0:
                root_task_ids.append(task_execution.id)

        return (
            WorkflowExecution(
                id=workflow_execution_id,
                workflow_definition_id=workflow_definition.id,
                status=WorkflowStatus.RUNNING,
                task_executions=task_executions,
            ),
            root_task_ids,
        )

    def _create_child_task_lookup(
        self,
        task_definitions: list[TaskDefinition],
        task_execution_ids: dict[UUID, UUID],
    ) -> dict[UUID, list[UUID]]:
        """Build child execution identifiers for each task definition.

        Args:
            task_definitions: Task definitions belonging to the workflow.
            task_execution_ids: Mapping from task definition identifiers to newly
                generated task execution identifiers.

        Returns:
            Mapping from task definition identifiers to child task execution
            identifiers.
        """

        children: dict[UUID, list[UUID]] = {
            task_definition.id: [] for task_definition in task_definitions
        }

        for task_definition in task_definitions:
            task_execution_id = task_execution_ids[task_definition.id]

            for parent_id in task_definition.dependencies:
                children[parent_id].append(task_execution_id)

        return children
