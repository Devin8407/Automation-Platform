"""HTTP schemas for workflow definitions."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from ....application import (
    CreateTaskDefinition,
    CreateTriggerDefinition,
    CreateWorkflowDefinition,
)


class CreateTaskDefinitionRequest(BaseModel):
    """HTTP input for creating a task definition."""

    plugin_type: str
    key: str
    configuration: dict[str, Any] = Field(default_factory=dict)
    dependencies: list[str] = Field(default_factory=list)
    max_tries: int


class CreateTriggerDefinitionRequest(BaseModel):
    """HTTP input for creating a trigger definition."""

    plugin_type: str
    configuration: dict[str, Any] = Field(default_factory=dict)
    enabled: bool


class CreateWorkflowDefinitionRequest(BaseModel):
    """HTTP input for creating a workflow definition."""

    name: str
    description: str
    tasks: list[CreateTaskDefinitionRequest]
    triggers: list[CreateTriggerDefinitionRequest]
    enabled: bool

    def to_application_model(self) -> CreateWorkflowDefinition:
        """Convert the HTTP model into an application request model."""

        return CreateWorkflowDefinition(
            name=self.name,
            description=self.description,
            tasks=[
                CreateTaskDefinition(
                    plugin_type=task.plugin_type,
                    key=task.key,
                    configuration=task.configuration,
                    dependencies=task.dependencies,
                    max_tries=task.max_tries,
                )
                for task in self.tasks
            ],
            triggers=[
                CreateTriggerDefinition(
                    plugin_type=trigger.plugin_type,
                    configuration=trigger.configuration,
                    enabled=trigger.enabled,
                )
                for trigger in self.triggers
            ],
            enabled=self.enabled,
        )


class CreateWorkflowDefinitionResponse(BaseModel):
    """HTTP response after creating a workflow definition."""

    workflow_definition_id: UUID


class StartWorkflowResponse(BaseModel):
    """HTTP response after starting a workflow execution."""

    workflow_execution_id: UUID
