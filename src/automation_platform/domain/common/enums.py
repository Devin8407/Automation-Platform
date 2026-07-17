"""Shared domain enumerations."""

from enum import Enum, auto


class WorkflowStatus(Enum):
    """Current state of a workflow execution."""

    PENDING = auto()
    RUNNING = auto()
    COMPLETED = auto()
    FAILED = auto()
    CANCELLED = auto()


class TaskStatus(Enum):
    """Current state of a task execution."""

    PENDING = auto()
    QUEUED = auto()
    RUNNING = auto()
    COMPLETED = auto()
    FAILED = auto()
    CANCELLED = auto()
