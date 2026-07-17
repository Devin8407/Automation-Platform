"""
Trigger definition domain model.

Trigger definitions describe the conditions under which
a workflow should begin execution.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID


@dataclass(slots=True)
class TriggerDefinition:
    """Reusable definition of a workflow trigger."""

    id: UUID

    type: str

    configuration: dict[str, Any] = field(default_factory=dict)

    enabled: bool = True
