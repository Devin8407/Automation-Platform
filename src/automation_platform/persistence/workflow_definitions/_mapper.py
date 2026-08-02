"""
Maps workflow definition domain objects to SQLAlchemy models and back.

Repositories use these helpers to translate between the domain model and the
Persistence Layer. Mappers contain no database logic and perform no queries.
"""

from __future__ import annotations

from uuid import UUID

from automation_platform.domain.workflow_definitions import (
    TaskDefinition,
    TriggerDefinition,
    WorkflowDefinition,
)

from ._model import (
    TaskDefinitionDependencyModel,
    TaskDefinitionModel,
    TriggerDefinitionModel,
    WorkflowDefinitionModel,
)


class WorkflowDefinitionMapper:
    """Converts workflow definition domain objects and SQLAlchemy models."""

    @staticmethod
    def workflow_to_model(workflow: WorkflowDefinition) -> WorkflowDefinitionModel:
        """Convert a workflow definition into its SQLAlchemy model.

        Args:
            workflow: Domain workflow definition.

        Returns:
            SQLAlchemy workflow definition model.
        """
        return WorkflowDefinitionModel(
            id=workflow.id,
            name=workflow.name,
            description=workflow.description,
            enabled=workflow.enabled,
        )

    @staticmethod
    def workflow_to_domain(
        model: WorkflowDefinitionModel,
        task_definitions: list[TaskDefinition],
        trigger_definitions: list[TriggerDefinition],
    ) -> WorkflowDefinition:
        """Convert a workflow definition model into a domain object.

        Args:
            model: SQLAlchemy workflow definition model.
            task_definitions: Domain task definitions belonging to the workflow.
            trigger_definitions: Domain trigger definitions belonging to the workflow.

        Returns:
            Domain workflow definition.
        """
        return WorkflowDefinition(
            id=model.id,
            name=model.name,
            description=model.description,
            enabled=model.enabled,
            task_definitions=task_definitions,
            trigger_definitions=trigger_definitions,
        )

    @staticmethod
    def task_to_model(workflow_definition_id: UUID, task: TaskDefinition) -> TaskDefinitionModel:
        """Convert a task definition into its SQLAlchemy model.

        Args:
            workflow_definition_id: Owning workflow definition identifier.
            task: Domain task definition.

        Returns:
            SQLAlchemy task definition model.
        """
        return TaskDefinitionModel(
            id=task.id,
            workflow_definition_id=workflow_definition_id,
            key=task.key,
            plugin_type=task.plugin_type,
            configuration=task.configuration,
            max_tries=task.max_tries,
        )

    @staticmethod
    def task_to_domain(model: TaskDefinitionModel, dependency_ids: list[UUID]) -> TaskDefinition:
        """Convert a task definition model into a domain object.

        Args:
            model: SQLAlchemy task definition model.
            dependency_ids: Identifiers of tasks this task depends on.

        Returns:
            Domain task definition.
        """
        return TaskDefinition(
            id=model.id,
            key=model.key,
            plugin_type=model.plugin_type,
            configuration=model.configuration,
            dependencies=dependency_ids,
            max_tries=model.max_tries,
        )

    @staticmethod
    def trigger_to_model(
        workflow_definition_id: UUID,
        trigger: TriggerDefinition,
    ) -> TriggerDefinitionModel:
        """Convert a trigger definition into its SQLAlchemy model.

        Args:
            workflow_definition_id: Owning workflow definition identifier.
            trigger: Domain trigger definition.

        Returns:
            SQLAlchemy trigger definition model.
        """
        return TriggerDefinitionModel(
            id=trigger.id,
            workflow_definition_id=workflow_definition_id,
            plugin_type=trigger.plugin_type,
            configuration=trigger.configuration,
            enabled=trigger.enabled,
        )

    @staticmethod
    def trigger_to_domain(model: TriggerDefinitionModel) -> TriggerDefinition:
        """Convert a trigger definition model into a domain object.

        Args:
            model: SQLAlchemy trigger definition model.

        Returns:
            Domain trigger definition.
        """
        return TriggerDefinition(
            id=model.id,
            plugin_type=model.plugin_type,
            configuration=model.configuration,
            enabled=model.enabled,
        )

    @staticmethod
    def dependency_to_model(
        task_definition_id: UUID,
        depends_on_task_definition_id: UUID,
    ) -> TaskDefinitionDependencyModel:
        """Convert a task dependency into its SQLAlchemy model.

        Args:
            task_definition_id: Identifier of the dependent task.
            depends_on_task_definition_id: Identifier of the task that must complete first.

        Returns:
            SQLAlchemy task dependency model.
        """
        return TaskDefinitionDependencyModel(
            task_definition_id=task_definition_id,
            depends_on_task_definition_id=depends_on_task_definition_id,
        )

    @staticmethod
    def dependencies_to_models(task: TaskDefinition) -> list[TaskDefinitionDependencyModel]:
        """Convert a task's dependencies into SQLAlchemy models.

        Args:
            task: Domain task definition.

        Returns:
            Dependency models representing each dependency edge.
        """
        return [
            WorkflowDefinitionMapper.dependency_to_model(
                task.id,
                dependency_id,
            )
            for dependency_id in task.dependencies
        ]
