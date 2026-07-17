"""
Task definition domain model.

Task definitions describe the reusable structure of an individual
task within a workflow.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID


@dataclass(slots=True)
class TaskDefinition:
    """Reusable definition of a workflow task."""

    id: UUID

    type: str

    configuration: dict[str, Any] = field(default_factory=dict)

    dependencies: list[UUID] = field(default_factory=list)

    max_retries: int = 0
