"""
Task output domain model.

Task output represent the runtime output of an executed task plugin.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class TaskOutput:
    """Runtime output of an executed plugin task."""

    values: dict[str, Any] = field(default_factory=dict)
