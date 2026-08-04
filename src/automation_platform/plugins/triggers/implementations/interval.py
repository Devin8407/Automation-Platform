"""Interval-based chronological trigger plugin."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from ...exceptions import InvalidPluginConfigurationError
from ..mechanisms import ChronologicalTrigger


class IntervalTrigger(ChronologicalTrigger):
    """Trigger that occurs repeatedly at a fixed time interval."""

    plugin_type = "interval"

    @classmethod
    def validate_configuration(
        cls,
        configuration: dict[str, Any],
    ) -> None:
        """Validate interval trigger configuration.

        Args:
            configuration: Plugin-specific configuration to validate.

        Raises:
            InvalidPluginConfigurationError: If interval_seconds is missing,
                is not an integer, or is not positive.
        """

        interval_seconds = configuration.get("interval_seconds")

        if not isinstance(interval_seconds, int) or isinstance(interval_seconds, bool):
            raise InvalidPluginConfigurationError("interval_seconds must be an integer.")

        if interval_seconds <= 0:
            raise InvalidPluginConfigurationError("interval_seconds must be greater than zero.")

        if set(configuration) != {"interval_seconds"}:
            raise InvalidPluginConfigurationError(
                "Interval trigger configuration must contain only interval_seconds."
            )

    @classmethod
    def next_occurrence(
        cls,
        configuration: dict[str, Any],
        after: datetime,
    ) -> datetime:
        """Calculate the next occurrence after the given time.

        Args:
            configuration: Validated interval trigger configuration.
            after: Time from which to calculate the next occurrence.

        Returns:
            The next scheduled occurrence.
        """
        return after + timedelta(seconds=configuration["interval_seconds"])
