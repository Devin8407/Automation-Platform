"""workflow definitions service models."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class CreateWorkflowDefinition:
    """Inputs to create a workflow definition."""

    name: str
    description: str
    tasks: list[CreateTaskDefinition]
    triggers: list[CreateTriggerDefinition]
    enabled: bool


@dataclass(frozen=True)
class CreateTaskDefinition:
    """Inputs to create a task definition."""

    plugin_type: str
    key: str
    configuration: dict[str, Any]
    dependencies: list[str]
    max_tries: int


@dataclass(frozen=True)
class CreateTriggerDefinition:
    """iInputs to create a trigger definition."""

    plugin_type: str
    configuration: dict[str, Any]
    enabled: bool
