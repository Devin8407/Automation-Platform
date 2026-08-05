"""Application services for managing workflow definitions."""

from typing import Callable
from uuid import UUID, uuid4

from ...domain import TaskDefinition, TriggerDefinition, WorkflowDefinition
from ...persistence import UnitOfWork
from ...plugins import (
    InvalidPluginConfigurationError,
    TaskRegistry,
    Trigger,
    TriggerRegistry,
)
from ..exceptions import InvalidWorkflowDefinitionError
from ..trigger_initialization import TriggerInitializationService
from .models import CreateTaskDefinition, CreateTriggerDefinition, CreateWorkflowDefinition


class WorkflowDefinitionService:
    """Coordinates workflow definition creation and deletion."""

    # ==============================================================================================
    # Constructor
    # ==============================================================================================

    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        task_registry: TaskRegistry,
        trigger_registry: TriggerRegistry,
        trigger_initialization_service: TriggerInitializationService,
    ) -> None:
        """Initialize the workflow definition service.

        Args:
            uow_factory: Factory for creating persistence units of work.
            task_registry: Registry of available task plugins.
            trigger_registry: Registry of available trigger plugins.
            trigger_initialization_service: Service for initializing trigger
                mechanism state.
        """

        self._uow_factory = uow_factory
        self._task_registry = task_registry
        self._trigger_registry = trigger_registry
        self._trigger_initialization_service = trigger_initialization_service

    # ==============================================================================================
    # Public API
    # ==============================================================================================

    def create(self, request: CreateWorkflowDefinition) -> UUID:
        """Create and persist a workflow definition.

        Validates the workflow definition, persists it, initializes any
        mechanism-specific trigger state, and commits the complete definition
        atomically.

        Args:
            request: Inputs describing the workflow definition to create.

        Returns:
            Identifier of the created workflow definition.

        Raises:
            InvalidWorkflowDefinitionError: If the workflow definition is invalid.
        """

        self._validate_tasks(request.tasks)
        task_definitions = self._create_task_definitions(request.tasks)

        resolved_triggers = self._create_trigger_definitions(request.triggers)

        workflow_definition = WorkflowDefinition(
            id=uuid4(),
            name=request.name,
            description=request.description,
            task_definitions=task_definitions,
            trigger_definitions=[trigger_definition for trigger_definition, _ in resolved_triggers],
            enabled=request.enabled,
        )

        with self._uow_factory() as uow:
            uow.workflow_definitions.save(workflow_definition)

            uow.flush()

            for trigger_definition, trigger_plugin in resolved_triggers:
                self._trigger_initialization_service.initialize(
                    trigger_plugin,
                    trigger_definition,
                    uow,
                )

            uow.commit()

        return workflow_definition.id

    def delete(self, workflow_definition_id: UUID) -> None:
        """Delete a workflow definition.

        Args:
            workflow_definition_id: Identifier of the workflow definition to delete.
        """

        with self._uow_factory() as uow:
            uow.workflow_definitions.delete(workflow_definition_id)
            uow.commit()

    # ==============================================================================================
    # Private Helpers
    # ==============================================================================================

    def _validate_tasks(self, tasks: list[CreateTaskDefinition]) -> None:
        """Validate task definitions and their dependency graph.

        Args:
            tasks: Task definitions to validate.

        Raises:
            InvalidWorkflowDefinitionError: If a task or dependency is invalid.
        """

        if not tasks:
            raise InvalidWorkflowDefinitionError(
                "Workflow definition must contain at least one task."
            )

        seen_keys = {task.key for task in tasks}

        if len(seen_keys) != len(tasks):
            raise InvalidWorkflowDefinitionError("Task keys are not all unique in workflow.")

        for task in tasks:
            if task.max_tries < 1:
                raise InvalidWorkflowDefinitionError(
                    f"Task {task.key!r} has no available max tries: {task.max_tries!r}."
                )

            if not self._task_registry.contains(task.plugin_type):
                raise InvalidWorkflowDefinitionError(
                    f"Unknown task plugin type: {task.plugin_type!r}."
                )

            try:
                plugin = self._task_registry.get(task.plugin_type)
                plugin.validate_configuration(task.configuration)
            except InvalidPluginConfigurationError as exc:
                raise InvalidWorkflowDefinitionError(
                    f"Invalid configuration for task {task.key!r}: {exc}"
                ) from exc

            if task.key in task.dependencies:
                raise InvalidWorkflowDefinitionError(f"Task {task.key!r} depends on self.")

            if len(task.dependencies) != len(set(task.dependencies)):
                raise InvalidWorkflowDefinitionError(
                    f"Task {task.key!r} has duplicate dependencies."
                )

            for dependency in task.dependencies:
                if dependency not in seen_keys:
                    raise InvalidWorkflowDefinitionError(
                        f"Task {task.key!r} references unknown dependency {dependency!r}."
                    )

        if self._has_dependency_cycle(tasks):
            raise InvalidWorkflowDefinitionError("Task dependency graph contains a cycle.")

    def _has_dependency_cycle(self, tasks: list[CreateTaskDefinition]) -> bool:
        """Determine whether the task dependency graph contains a cycle.

        Args:
            tasks: Task definitions whose dependencies form the graph.

        Returns:
            True if the dependency graph contains a cycle; otherwise False.
        """

        remaining_dependencies = {task.key: len(task.dependencies) for task in tasks}

        children: dict[str, list[str]] = {task.key: [] for task in tasks}

        for task in tasks:
            for dependency in task.dependencies:
                children[dependency].append(task.key)

        ready = [
            key for key, dependency_count in remaining_dependencies.items() if dependency_count == 0
        ]

        processed = 0

        while ready:
            key = ready.pop()
            processed += 1

            for child in children[key]:
                remaining_dependencies[child] -= 1

                if remaining_dependencies[child] == 0:
                    ready.append(child)

        return processed != len(tasks)

    def _validate_triggers(
        self,
        triggers: list[CreateTriggerDefinition],
    ) -> list[type[Trigger]]:
        """Validate trigger definitions and resolve their plugins.

        Args:
            triggers: Trigger definitions to validate.

        Returns:
            Resolved trigger plugins corresponding to the validated definitions.

        Raises:
            InvalidWorkflowDefinitionError: If a trigger definition is invalid.
        """

        resolved_plugins: list[type[Trigger]] = []

        for trigger in triggers:
            if not self._trigger_registry.contains(trigger.plugin_type):
                raise InvalidWorkflowDefinitionError(
                    f"Unknown trigger plugin type: {trigger.plugin_type!r}."
                )

            try:
                plugin = self._trigger_registry.get(trigger.plugin_type)
                plugin.validate_configuration(trigger.configuration)
            except InvalidPluginConfigurationError as exc:
                raise InvalidWorkflowDefinitionError(
                    f"Invalid configuration for trigger {trigger.plugin_type!r}: {exc}"
                ) from exc

            resolved_plugins.append(plugin)

        return resolved_plugins

    def _create_task_definitions(
        self,
        tasks: list[CreateTaskDefinition],
    ) -> list[TaskDefinition]:
        """Create domain task definitions from application inputs.

        Args:
            tasks: Validated task definition inputs.

        Returns:
            Domain task definitions with resolved dependency identifiers.
        """

        task_ids = {task.key: uuid4() for task in tasks}

        return [
            TaskDefinition(
                id=task_ids[task.key],
                plugin_type=task.plugin_type,
                key=task.key,
                configuration=task.configuration,
                dependencies=[task_ids[dependency] for dependency in task.dependencies],
                max_tries=task.max_tries,
            )
            for task in tasks
        ]

    def _create_trigger_definitions(
        self,
        triggers: list[CreateTriggerDefinition],
    ) -> list[tuple[TriggerDefinition, type[Trigger]]]:
        """Validate trigger inputs and create their domain definitions."""

        trigger_definitions = []

        for trigger in triggers:
            if not self._trigger_registry.contains(trigger.plugin_type):
                raise InvalidWorkflowDefinitionError(
                    f"Unknown trigger plugin type: {trigger.plugin_type!r}."
                )

            try:
                plugin = self._trigger_registry.get(trigger.plugin_type)
                plugin.validate_configuration(trigger.configuration)
            except InvalidPluginConfigurationError as exc:
                raise InvalidWorkflowDefinitionError(
                    f"Invalid configuration for trigger {trigger.plugin_type!r}: {exc}"
                ) from exc

            trigger_definition = TriggerDefinition(
                id=uuid4(),
                plugin_type=trigger.plugin_type,
                configuration=trigger.configuration,
                enabled=trigger.enabled,
            )

            trigger_definitions.append((trigger_definition, plugin))

        return trigger_definitions
