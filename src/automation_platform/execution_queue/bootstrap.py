"""
Queue bootstrap.

Constructs and wires together the specified Queue implementation
from application configuration.

This module serves as the composition root for the Queue Layer.
"""

from ..infrastructure import Infrastructure
from .exceptions import InvalidExecutionQueueType
from .interface import ExecutionQueue
from .postgres import PostgresExecutionQueue


def build_execution_queue(infrastructure: Infrastructure) -> ExecutionQueue:
    """
    Build the Queue.

    Args:
        settings: Application configuration.

    Returns:
        A configured Execution Queue.
    """

    queue_type = infrastructure.settings.queue_type

    if queue_type == "postgres":
        return PostgresExecutionQueue(
            infrastructure.session_factory,
            infrastructure.settings.queue_lease_timeout,
        )

    raise InvalidExecutionQueueType(f"Configured with invalid execution type: {queue_type!r}")
