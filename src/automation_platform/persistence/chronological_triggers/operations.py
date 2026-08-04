"""
Chronological trigger persistence results models..
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID


@dataclass(frozen=True)
class DueChronologicalTrigger:
    """Persisted data for a due chronological trigger."""

    trigger_definition_id: UUID
    workflow_definition_id: UUID
    plugin_type: str
    configuration: dict[str, Any]
    next_run_at: datetime
