"""Base interface for chronological workflow trigger plugins."""

from __future__ import annotations

from abc import abstractmethod
from datetime import datetime
from typing import Any

from ..interface import Trigger


class ChronologicalTrigger(Trigger):
    """Base interface for time-based workflow trigger plugins."""

    @classmethod
    @abstractmethod
    def next_occurrence(
        cls,
        configuration: dict[str, Any],
        after: datetime,
    ) -> datetime | None:
        """Calculate the next trigger occurrence after a given time.

        Args:
            configuration: Plugin-specific trigger configuration.
            after: Time after which to calculate the next occurrence.

        Returns:
            The next occurrence, or None if there is no future occurrence.
        """

        ...
