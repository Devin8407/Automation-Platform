"""
Repository for workflow definitions.
"""

from __future__ import annotations

from collections import defaultdict
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from automation_platform.domain.workflow_definitions import WorkflowDefinition

from ._mapper import TaskDefinitionModel, WorkflowDefinitionMapper
from ._model import (
    TaskDefinitionDependencyModel,
    TriggerDefinitionModel,
    WorkflowDefinitionModel,
)


class WorkflowDefinitionRepository:
    """Persists workflow definitions using SQLAlchemy."""

    def __init__(self, session: Session) -> None:
        """Initialize the repository.

        Args:
            session: SQLAlchemy session.
        """
        self._session = session

    def load(self, workflow_definition_id: UUID) -> WorkflowDefinition | None:
        """Load a workflow definition.

        Args:
            workflow_definition_id: Identifier of the workflow definition.

        Returns:
            The loaded workflow definition if found; otherwise None.
        """

        workflow_model = self._session.get(WorkflowDefinitionModel, workflow_definition_id)

        if workflow_model is None:
            return None

        dependency_lookup = self._load_dependency_lookup(workflow_model.id)

        task_definitions = [
            WorkflowDefinitionMapper.task_to_domain(
                task_model,
                dependency_lookup.get(task_model.id, []),
            )
            for task_model in workflow_model.task_definitions
        ]

        trigger_definitions = [
            WorkflowDefinitionMapper.trigger_to_domain(trigger_model)
            for trigger_model in workflow_model.trigger_definitions
        ]

        return WorkflowDefinitionMapper.workflow_to_domain(
            workflow_model,
            task_definitions,
            trigger_definitions,
        )

    def save(self, workflow_definition: WorkflowDefinition) -> None:
        """Persist a workflow definition.

        Args:
            workflow_definition: Workflow definition to persist.
        """

        workflow_model = WorkflowDefinitionMapper.workflow_to_model(workflow_definition)
        self._session.merge(workflow_model)

        self._synchronize_tasks(workflow_definition)
        self._synchronize_triggers(workflow_definition)

    def delete(self, workflow_definition_id: UUID) -> None:
        """Delete a workflow definition.

        Args:
            workflow_definition_id: Identifier of the workflow definition.
        """

        model = self._session.get(WorkflowDefinitionModel, workflow_definition_id)

        if model is not None:
            self._session.delete(model)

    def _load_dependency_lookup(self, workflow_definition_id: UUID) -> dict[UUID, list[UUID]]:
        """Build a lookup of task dependency identifiers.

        Args:
            workflow_definition_id: Workflow definition identifier.

        Returns:
            Mapping of task identifiers to dependency identifiers.
        """

        rows = self._session.scalars(
            select(TaskDefinitionDependencyModel)
            .join(
                TaskDefinitionModel,
                TaskDefinitionDependencyModel.task_definition_id == TaskDefinitionModel.id,
            )
            .where(TaskDefinitionModel.workflow_definition_id == workflow_definition_id)
        )

        lookup: defaultdict[UUID, list[UUID]] = defaultdict(list)

        for row in rows:
            lookup[row.task_definition_id].append(row.depends_on_task_definition_id)

        return dict(lookup)

    def _synchronize_tasks(
        self,
        workflow_definition: WorkflowDefinition,
    ) -> None:
        """Synchronize task definitions and dependencies."""

        current_task_ids = {task.id for task in workflow_definition.task_definitions}

        self._session.execute(
            delete(TaskDefinitionModel).where(
                TaskDefinitionModel.workflow_definition_id == workflow_definition.id,
                TaskDefinitionModel.id.not_in(current_task_ids),
            )
        )

        for task in workflow_definition.task_definitions:
            self._session.merge(
                WorkflowDefinitionMapper.task_to_model(
                    workflow_definition.id,
                    task,
                )
            )

            self._session.execute(
                delete(TaskDefinitionDependencyModel).where(
                    TaskDefinitionDependencyModel.task_definition_id == task.id
                )
            )

            for dependency in WorkflowDefinitionMapper.dependencies_to_models(task):
                self._session.merge(dependency)

    def _synchronize_triggers(
        self,
        workflow_definition: WorkflowDefinition,
    ) -> None:
        """Synchronize trigger definitions."""

        current_trigger_ids = {trigger.id for trigger in workflow_definition.trigger_definitions}

        self._session.execute(
            delete(TriggerDefinitionModel).where(
                TriggerDefinitionModel.workflow_definition_id == workflow_definition.id,
                TriggerDefinitionModel.id.not_in(current_trigger_ids),
            )
        )

        for trigger in workflow_definition.trigger_definitions:
            self._session.merge(
                WorkflowDefinitionMapper.trigger_to_model(
                    workflow_definition.id,
                    trigger,
                )
            )
