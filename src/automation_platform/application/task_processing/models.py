"""Task processing application models."""

from dataclasses import dataclass, field
from uuid import UUID


@dataclass(frozen=True)
class ProcessTaskResult:
    """Result of processing a task execution."""

    enqueue_task_ids: list[UUID] = field(default_factory=list)
    should_retry: bool = False
