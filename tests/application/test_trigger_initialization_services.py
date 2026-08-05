"""Tests for the trigger initialization application service."""

from unittest.mock import MagicMock

from automation_platform.application import TriggerInitializationService
from automation_platform.plugins import Trigger
from automation_platform.plugins.triggers import ChronologicalTrigger

# ==================================================================================================
# Test Trigger Types
# ==================================================================================================


class TestChronologicalTrigger(ChronologicalTrigger):
    """Chronological trigger implementation used for dispatch tests."""

    plugin_type = "test_chronological"

    @classmethod
    def next_occurrence(cls, configuration, after):
        """Return no next occurrence."""

        return None


class TestChronologicalTriggerSubclass(TestChronologicalTrigger):
    """Subclass of a chronological trigger implementation."""

    plugin_type = "test_chronological_subclass"


class UnsupportedTrigger(Trigger):
    """Trigger without a registered initialization mechanism."""

    plugin_type = "unsupported"


# ==================================================================================================
# Chronological Trigger Dispatch
# ==================================================================================================


def test_initialize_dispatches_chronological_trigger(
    trigger_definition_factory,
    mock_uow,
):
    """Chronological triggers should dispatch to the chronological initializer."""

    chronological_trigger_service = MagicMock()

    service = TriggerInitializationService(
        chronological_trigger_service=chronological_trigger_service,
    )

    trigger_definition = trigger_definition_factory(
        plugin_type="test_chronological",
    )

    service.initialize(
        TestChronologicalTrigger,
        trigger_definition,
        mock_uow,
    )

    chronological_trigger_service.initialize.assert_called_once_with(
        TestChronologicalTrigger,
        trigger_definition,
        mock_uow,
    )


def test_initialize_dispatches_chronological_trigger_subclass(
    trigger_definition_factory,
    mock_uow,
):
    """Chronological trigger subclasses should use the chronological initializer."""

    chronological_trigger_service = MagicMock()

    service = TriggerInitializationService(
        chronological_trigger_service=chronological_trigger_service,
    )

    trigger_definition = trigger_definition_factory(
        plugin_type="test_chronological_subclass",
    )

    service.initialize(
        TestChronologicalTriggerSubclass,
        trigger_definition,
        mock_uow,
    )

    chronological_trigger_service.initialize.assert_called_once_with(
        TestChronologicalTriggerSubclass,
        trigger_definition,
        mock_uow,
    )


# ==================================================================================================
# Unsupported Trigger Mechanism
# ==================================================================================================


def test_initialize_does_nothing_for_unsupported_trigger_mechanism(
    trigger_definition_factory,
    mock_uow,
):
    """Triggers without a registered mechanism should require no initialization."""

    chronological_trigger_service = MagicMock()

    service = TriggerInitializationService(
        chronological_trigger_service=chronological_trigger_service,
    )

    trigger_definition = trigger_definition_factory(
        plugin_type="unsupported",
    )

    service.initialize(
        UnsupportedTrigger,
        trigger_definition,
        mock_uow,
    )

    chronological_trigger_service.initialize.assert_not_called()
