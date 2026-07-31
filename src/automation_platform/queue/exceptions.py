"""Exceptions raised by the queue subsystem."""

from __future__ import annotations


class QueueError(Exception):
    """Base exception for queue-related errors."""


class ClaimLostError(QueueError):
    """Raised when a worker attempts to operate on a lease it no longer owns.

    This exception indicates that the claim has expired or has been reclaimed
    by another worker. No queue modifications are performed when this occurs.
    """
