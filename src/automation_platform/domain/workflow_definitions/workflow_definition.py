"""
Workflow definition domain model.

Workflow definitions describe reusable automation workflows.
They are immutable templates from which workflow executions
are created.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from .task_definition import TaskDefinition
from .trigger_definition import TriggerDefinition


@dataclass(slots=True)
class WorkflowDefinition:
    """Reusable definition of an automation workflow."""

    id: UUID

    name: str
    description: str = ""

    task_definitions: list[TaskDefinition] = field(default_factory=list)
    trigger_definitions: list[TriggerDefinition] = field(default_factory=list)

    enabled: bool = True
