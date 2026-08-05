"""Tests for the chronological trigger application service."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from automation_platform.persistence.chronological_triggers.operations import (
    DueChronologicalTrigger,
)

# ==================================================================================================
# Helpers
# ==================================================================================================


def _due_trigger(
    *,
    configuration: dict | None = None,
    next_run_at: datetime | None = None,
) -> DueChronologicalTrigger:
    """Create a due chronological trigger for service tests."""

    return DueChronologicalTrigger(
        trigger_definition_id=uuid4(),
        workflow_definition_id=uuid4(),
        plugin_type="interval",
        configuration=configuration or {"seconds": 60},
        next_run_at=next_run_at or datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc),
    )


# ==================================================================================================
# Initialization
# ==================================================================================================


def test_initialize_creates_scheduling_state(
    mock_chronological_trigger_service,
    trigger_definition_factory,
    mock_trigger_plugin_type,
    mock_uow,
):
    """Initialization should persist the trigger's first occurrence."""

    trigger_definition = trigger_definition_factory(
        plugin_type="interval",
        configuration={"seconds": 60},
    )
    next_run_at = datetime(
        2026,
        1,
        1,
        12,
        1,
        tzinfo=timezone.utc,
    )

    mock_trigger_plugin_type.next_occurrence.return_value = next_run_at

    mock_chronological_trigger_service.initialize(
        mock_trigger_plugin_type,
        trigger_definition,
        mock_uow,
    )

    mock_trigger_plugin_type.next_occurrence.assert_called_once()

    configuration, now = mock_trigger_plugin_type.next_occurrence.call_args.args

    assert configuration == trigger_definition.configuration
    assert now.tzinfo is not None

    mock_uow.chronological_triggers.create.assert_called_once_with(
        trigger_definition.id,
        next_run_at,
    )


def test_initialize_does_not_create_state_without_next_occurrence(
    mock_chronological_trigger_service,
    trigger_definition_factory,
    mock_trigger_plugin_type,
    mock_uow,
):
    """Initialization should do nothing when no occurrence exists."""

    trigger_definition = trigger_definition_factory(
        plugin_type="interval",
    )

    mock_trigger_plugin_type.next_occurrence.return_value = None

    mock_chronological_trigger_service.initialize(
        mock_trigger_plugin_type,
        trigger_definition,
        mock_uow,
    )

    mock_uow.chronological_triggers.create.assert_not_called()


def test_initialize_does_not_commit(
    mock_chronological_trigger_service,
    trigger_definition_factory,
    mock_trigger_plugin_type,
    mock_uow,
):
    """Initialization should leave transaction ownership with the caller."""

    trigger_definition = trigger_definition_factory(
        plugin_type="interval",
    )

    mock_trigger_plugin_type.next_occurrence.return_value = datetime(
        2026,
        1,
        1,
        12,
        1,
        tzinfo=timezone.utc,
    )

    mock_chronological_trigger_service.initialize(
        mock_trigger_plugin_type,
        trigger_definition,
        mock_uow,
    )

    mock_uow.commit.assert_not_called()


# ==================================================================================================
# No Due Trigger
# ==================================================================================================


def test_process_next_due_returns_false_when_nothing_is_due(
    mock_chronological_trigger_service,
    mock_uow,
    mock_trigger_registry,
    mock_workflow_start_service_dependency,
):
    """Processing should return False when no trigger is currently due."""

    mock_uow.chronological_triggers.get_next_due.return_value = None

    result = mock_chronological_trigger_service.process_next_due()

    assert result is False

    mock_uow.chronological_triggers.get_next_due.assert_called_once()

    now = mock_uow.chronological_triggers.get_next_due.call_args.args[0]

    assert now.tzinfo is not None

    mock_trigger_registry.get.assert_not_called()
    mock_uow.chronological_triggers.update_next_run.assert_not_called()
    mock_uow.chronological_triggers.delete.assert_not_called()
    mock_workflow_start_service_dependency.start_and_commit.assert_not_called()


# ==================================================================================================
# Recurring Trigger
# ==================================================================================================


def test_process_next_due_updates_next_occurrence(
    mock_chronological_trigger_service,
    mock_uow,
    mock_trigger_registry,
    mock_trigger_plugin_type,
):
    """Processing a recurring trigger should advance its scheduling state."""

    due_trigger = _due_trigger(
        configuration={"seconds": 60},
    )
    next_run_at = due_trigger.next_run_at + timedelta(seconds=60)

    mock_uow.chronological_triggers.get_next_due.return_value = due_trigger
    mock_trigger_plugin_type.next_occurrence.return_value = next_run_at

    result = mock_chronological_trigger_service.process_next_due()

    assert result is True

    mock_trigger_registry.get.assert_called_once_with(due_trigger.plugin_type)

    mock_trigger_plugin_type.next_occurrence.assert_called_once_with(
        due_trigger.configuration,
        due_trigger.next_run_at,
    )

    mock_uow.chronological_triggers.update_next_run.assert_called_once_with(
        due_trigger.trigger_definition_id,
        next_run_at,
    )

    mock_uow.chronological_triggers.delete.assert_not_called()


def test_process_next_due_starts_associated_workflow_with_same_uow(
    mock_chronological_trigger_service,
    mock_uow,
    mock_trigger_plugin_type,
    mock_workflow_start_service_dependency,
):
    """Processing should start the associated workflow using the claimed UoW."""

    due_trigger = _due_trigger()

    mock_uow.chronological_triggers.get_next_due.return_value = due_trigger
    mock_trigger_plugin_type.next_occurrence.return_value = due_trigger.next_run_at + timedelta(
        minutes=1
    )

    result = mock_chronological_trigger_service.process_next_due()

    assert result is True

    mock_workflow_start_service_dependency.start_and_commit.assert_called_once_with(
        due_trigger.workflow_definition_id,
        mock_uow,
    )


def test_process_next_due_updates_state_before_starting_workflow(
    mock_chronological_trigger_service,
    mock_uow,
    mock_trigger_plugin_type,
    mock_workflow_start_service_dependency,
):
    """Scheduling state should advance before workflow start commits the UoW."""

    due_trigger = _due_trigger()
    next_run_at = due_trigger.next_run_at + timedelta(minutes=1)

    mock_uow.chronological_triggers.get_next_due.return_value = due_trigger
    mock_trigger_plugin_type.next_occurrence.return_value = next_run_at

    events = []

    mock_uow.chronological_triggers.update_next_run.side_effect = lambda *_: events.append("update")
    mock_workflow_start_service_dependency.start_and_commit.side_effect = lambda *_: events.append(
        "start"
    )

    mock_chronological_trigger_service.process_next_due()

    assert events == [
        "update",
        "start",
    ]


# ==================================================================================================
# Terminal Trigger
# ==================================================================================================


def test_process_next_due_deletes_state_without_next_occurrence(
    mock_chronological_trigger_service,
    mock_uow,
    mock_trigger_plugin_type,
    mock_workflow_start_service_dependency,
):
    """A trigger without another occurrence should have its state deleted."""

    due_trigger = _due_trigger()

    mock_uow.chronological_triggers.get_next_due.return_value = due_trigger
    mock_trigger_plugin_type.next_occurrence.return_value = None

    result = mock_chronological_trigger_service.process_next_due()

    assert result is True

    mock_uow.chronological_triggers.delete.assert_called_once_with(
        due_trigger.trigger_definition_id
    )

    mock_uow.chronological_triggers.update_next_run.assert_not_called()

    mock_workflow_start_service_dependency.start_and_commit.assert_called_once_with(
        due_trigger.workflow_definition_id,
        mock_uow,
    )


def test_process_next_due_deletes_state_before_starting_workflow(
    mock_chronological_trigger_service,
    mock_uow,
    mock_trigger_plugin_type,
    mock_workflow_start_service_dependency,
):
    """Terminal scheduling state should be deleted before workflow start."""

    due_trigger = _due_trigger()

    mock_uow.chronological_triggers.get_next_due.return_value = due_trigger
    mock_trigger_plugin_type.next_occurrence.return_value = None

    events = []

    mock_uow.chronological_triggers.delete.side_effect = lambda *_: events.append("delete")
    mock_workflow_start_service_dependency.start_and_commit.side_effect = lambda *_: events.append(
        "start"
    )

    mock_chronological_trigger_service.process_next_due()

    assert events == [
        "delete",
        "start",
    ]


# ==================================================================================================
# Failure Boundaries
# ==================================================================================================


def test_process_next_due_does_not_start_workflow_when_trigger_fails(
    mock_chronological_trigger_service,
    mock_uow,
    mock_trigger_plugin_type,
    mock_workflow_start_service_dependency,
):
    """Workflow start should not occur when recurrence calculation fails."""

    due_trigger = _due_trigger()

    mock_uow.chronological_triggers.get_next_due.return_value = due_trigger
    mock_trigger_plugin_type.next_occurrence.side_effect = RuntimeError("Trigger failed.")

    with pytest.raises(RuntimeError, match="Trigger failed"):
        mock_chronological_trigger_service.process_next_due()

    mock_uow.chronological_triggers.update_next_run.assert_not_called()
    mock_uow.chronological_triggers.delete.assert_not_called()
    mock_workflow_start_service_dependency.start_and_commit.assert_not_called()


def test_process_next_due_propagates_workflow_start_failure(
    mock_chronological_trigger_service,
    mock_uow,
    mock_trigger_plugin_type,
    mock_workflow_start_service_dependency,
):
    """Workflow start failure should propagate after scheduling state changes."""

    due_trigger = _due_trigger()
    next_run_at = due_trigger.next_run_at + timedelta(minutes=1)

    mock_uow.chronological_triggers.get_next_due.return_value = due_trigger
    mock_trigger_plugin_type.next_occurrence.return_value = next_run_at

    mock_workflow_start_service_dependency.start_and_commit.side_effect = RuntimeError(
        "Workflow start failed."
    )

    with pytest.raises(RuntimeError, match="Workflow start failed"):
        mock_chronological_trigger_service.process_next_due()

    mock_uow.chronological_triggers.update_next_run.assert_called_once_with(
        due_trigger.trigger_definition_id,
        next_run_at,
    )

    mock_workflow_start_service_dependency.start_and_commit.assert_called_once_with(
        due_trigger.workflow_definition_id,
        mock_uow,
    )
