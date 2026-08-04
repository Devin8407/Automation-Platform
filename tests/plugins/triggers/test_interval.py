"""Unit tests for the interval trigger plugin."""

from datetime import datetime, timezone

import pytest

from automation_platform.plugins.exceptions import InvalidPluginConfigurationError
from automation_platform.plugins.triggers.implementations.interval import IntervalTrigger


class TestIntervalTrigger:
    """Tests for IntervalTrigger."""

    def test_valid_configuration(self) -> None:
        configuration = {"interval_seconds": 60}

        IntervalTrigger.validate_configuration(configuration)

    @pytest.mark.parametrize(
        "configuration",
        [
            {},
            {"interval_seconds": 0},
            {"interval_seconds": -1},
            {"interval_seconds": 1.5},
            {"interval_seconds": "60"},
            {"interval_seconds": True},
            {"interval_seconds": None},
            {"interval_seconds": 60, "unexpected": "value"},
        ],
    )
    def test_invalid_configuration(
        self,
        configuration: dict,
    ) -> None:
        with pytest.raises(InvalidPluginConfigurationError):
            IntervalTrigger.validate_configuration(configuration)

    def test_next_occurrence(self) -> None:
        configuration = {"interval_seconds": 60}
        after = datetime(
            2026,
            8,
            3,
            12,
            30,
            0,
            tzinfo=timezone.utc,
        )

        result = IntervalTrigger.next_occurrence(
            configuration,
            after,
        )

        assert result == datetime(
            2026,
            8,
            3,
            12,
            31,
            0,
            tzinfo=timezone.utc,
        )
