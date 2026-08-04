"""Tests for the chronological trigger repository."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy.orm import Session, sessionmaker

from automation_platform.persistence.chronological_triggers._model import (
    ChronologicalTriggerStateModel,
)
from automation_platform.persistence.chronological_triggers.repository import (
    ChronologicalTriggerRepository,
)
from automation_platform.persistence.workflow_definitions._model import (
    TriggerDefinitionModel,
    WorkflowDefinitionModel,
)

# ==================================================================================================
# Private Helpers
# ==================================================================================================


def _create_workflow_definition(
    session: Session,
    *,
    workflow_definition_id: UUID | None = None,
) -> WorkflowDefinitionModel:
    """Create and persist a workflow definition."""

    workflow_definition = WorkflowDefinitionModel(
        id=workflow_definition_id or uuid4(),
        name="test-workflow",
        description="Workflow used by chronological trigger repository tests.",
        enabled=True,
    )

    session.add(workflow_definition)
    session.flush()

    return workflow_definition


def _create_trigger_definition(
    session: Session,
    *,
    workflow_definition_id: UUID,
    trigger_definition_id: UUID | None = None,
    plugin_type: str = "interval",
    configuration: dict | None = None,
    enabled: bool = True,
) -> TriggerDefinitionModel:
    """Create and persist a trigger definition."""

    trigger_definition = TriggerDefinitionModel(
        id=trigger_definition_id or uuid4(),
        workflow_definition_id=workflow_definition_id,
        plugin_type=plugin_type,
        configuration=configuration or {"seconds": 60},
        enabled=enabled,
    )

    session.add(trigger_definition)
    session.flush()

    return trigger_definition


# ==================================================================================================
# Tests
# ==================================================================================================


def test_create_persists_chronological_trigger_state(
    session: Session,
) -> None:
    """Creating state should persist its trigger ID and next run time."""

    workflow_definition = _create_workflow_definition(session)
    trigger_definition = _create_trigger_definition(
        session,
        workflow_definition_id=workflow_definition.id,
    )

    next_run_at = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)

    repository = ChronologicalTriggerRepository(session)

    repository.create(
        trigger_definition.id,
        next_run_at,
    )

    session.flush()

    state = session.get(
        ChronologicalTriggerStateModel,
        trigger_definition.id,
    )

    assert state is not None
    assert state.trigger_definition_id == trigger_definition.id
    assert state.next_run_at == next_run_at


def test_get_next_due_returns_none_when_no_state_exists(
    session: Session,
) -> None:
    """No chronological state should result in no due trigger."""

    repository = ChronologicalTriggerRepository(session)

    result = repository.get_next_due(
        datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
    )

    assert result is None


def test_get_next_due_returns_none_when_trigger_is_not_due(
    session: Session,
) -> None:
    """A trigger scheduled in the future should not be returned."""

    workflow_definition = _create_workflow_definition(session)
    trigger_definition = _create_trigger_definition(
        session,
        workflow_definition_id=workflow_definition.id,
    )

    now = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)

    repository = ChronologicalTriggerRepository(session)

    repository.create(
        trigger_definition.id,
        now + timedelta(minutes=1),
    )

    session.flush()

    result = repository.get_next_due(now)

    assert result is None


def test_get_next_due_ignores_disabled_trigger(
    session: Session,
) -> None:
    """A disabled trigger definition should not be returned."""

    workflow_definition = _create_workflow_definition(session)
    trigger_definition = _create_trigger_definition(
        session,
        workflow_definition_id=workflow_definition.id,
        enabled=False,
    )

    now = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)

    repository = ChronologicalTriggerRepository(session)

    repository.create(
        trigger_definition.id,
        now - timedelta(minutes=1),
    )

    session.flush()

    result = repository.get_next_due(now)

    assert result is None


def test_get_next_due_returns_due_trigger(
    session: Session,
) -> None:
    """A due enabled trigger should be returned with its persisted data."""

    workflow_definition = _create_workflow_definition(session)

    configuration = {
        "seconds": 30,
    }

    trigger_definition = _create_trigger_definition(
        session,
        workflow_definition_id=workflow_definition.id,
        plugin_type="interval",
        configuration=configuration,
    )

    now = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    next_run_at = now - timedelta(seconds=30)

    repository = ChronologicalTriggerRepository(session)

    repository.create(
        trigger_definition.id,
        next_run_at,
    )

    session.flush()

    result = repository.get_next_due(now)

    assert result is not None
    assert result.trigger_definition_id == trigger_definition.id
    assert result.workflow_definition_id == workflow_definition.id
    assert result.plugin_type == "interval"
    assert result.configuration == configuration
    assert result.next_run_at == next_run_at


def test_get_next_due_returns_earliest_due_trigger(
    session: Session,
) -> None:
    """The earliest scheduled due trigger should be returned first."""

    workflow_definition = _create_workflow_definition(session)

    later_trigger = _create_trigger_definition(
        session,
        workflow_definition_id=workflow_definition.id,
    )
    earlier_trigger = _create_trigger_definition(
        session,
        workflow_definition_id=workflow_definition.id,
    )

    now = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)

    repository = ChronologicalTriggerRepository(session)

    repository.create(
        later_trigger.id,
        now - timedelta(minutes=1),
    )
    repository.create(
        earlier_trigger.id,
        now - timedelta(minutes=2),
    )

    session.flush()

    result = repository.get_next_due(now)

    assert result is not None
    assert result.trigger_definition_id == earlier_trigger.id
    assert result.next_run_at == now - timedelta(minutes=2)


def test_get_next_due_orders_equal_times_by_trigger_definition_id(
    session: Session,
) -> None:
    """Equal run times should be ordered by trigger definition ID."""

    workflow_definition = _create_workflow_definition(session)

    lower_id = UUID("00000000-0000-0000-0000-000000000001")
    higher_id = UUID("00000000-0000-0000-0000-000000000002")

    higher_trigger = _create_trigger_definition(
        session,
        workflow_definition_id=workflow_definition.id,
        trigger_definition_id=higher_id,
    )
    lower_trigger = _create_trigger_definition(
        session,
        workflow_definition_id=workflow_definition.id,
        trigger_definition_id=lower_id,
    )

    next_run_at = datetime(2026, 1, 1, 11, 0, tzinfo=UTC)
    now = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)

    repository = ChronologicalTriggerRepository(session)

    repository.create(
        higher_trigger.id,
        next_run_at,
    )
    repository.create(
        lower_trigger.id,
        next_run_at,
    )

    session.flush()

    result = repository.get_next_due(now)

    assert result is not None
    assert result.trigger_definition_id == lower_id


def test_get_next_due_skips_future_trigger_and_returns_due_trigger(
    session: Session,
) -> None:
    """Future state should not prevent an existing due trigger from returning."""

    workflow_definition = _create_workflow_definition(session)

    future_trigger = _create_trigger_definition(
        session,
        workflow_definition_id=workflow_definition.id,
    )
    due_trigger = _create_trigger_definition(
        session,
        workflow_definition_id=workflow_definition.id,
    )

    now = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)

    repository = ChronologicalTriggerRepository(session)

    repository.create(
        future_trigger.id,
        now + timedelta(minutes=1),
    )
    repository.create(
        due_trigger.id,
        now - timedelta(minutes=1),
    )

    session.flush()

    result = repository.get_next_due(now)

    assert result is not None
    assert result.trigger_definition_id == due_trigger.id


def test_get_next_due_skips_disabled_trigger_and_returns_enabled_trigger(
    session: Session,
) -> None:
    """A disabled earlier trigger should not hide a later enabled trigger."""

    workflow_definition = _create_workflow_definition(session)

    disabled_trigger = _create_trigger_definition(
        session,
        workflow_definition_id=workflow_definition.id,
        enabled=False,
    )
    enabled_trigger = _create_trigger_definition(
        session,
        workflow_definition_id=workflow_definition.id,
        enabled=True,
    )

    now = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)

    repository = ChronologicalTriggerRepository(session)

    repository.create(
        disabled_trigger.id,
        now - timedelta(minutes=2),
    )
    repository.create(
        enabled_trigger.id,
        now - timedelta(minutes=1),
    )

    session.flush()

    result = repository.get_next_due(now)

    assert result is not None
    assert result.trigger_definition_id == enabled_trigger.id


def test_update_next_run_updates_existing_state(
    session: Session,
) -> None:
    """Updating next run should modify the persisted scheduling state."""

    workflow_definition = _create_workflow_definition(session)
    trigger_definition = _create_trigger_definition(
        session,
        workflow_definition_id=workflow_definition.id,
    )

    initial_next_run_at = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    updated_next_run_at = datetime(2026, 1, 1, 13, 0, tzinfo=UTC)

    repository = ChronologicalTriggerRepository(session)

    repository.create(
        trigger_definition.id,
        initial_next_run_at,
    )

    session.flush()

    repository.update_next_run(
        trigger_definition.id,
        updated_next_run_at,
    )

    session.flush()

    state = session.get(
        ChronologicalTriggerStateModel,
        trigger_definition.id,
    )

    assert state is not None
    assert state.next_run_at == updated_next_run_at


def test_update_next_run_raises_when_state_does_not_exist(
    session: Session,
) -> None:
    """Updating nonexistent chronological state should fail."""

    trigger_definition_id = uuid4()

    repository = ChronologicalTriggerRepository(session)

    with pytest.raises(
        ValueError,
        match=(
            "Chronological trigger state does not exist for "
            f"trigger definition {trigger_definition_id}"
        ),
    ):
        repository.update_next_run(
            trigger_definition_id,
            datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
        )


def test_get_next_due_skips_trigger_locked_by_another_session(
    session: Session,
    session_factory: sessionmaker[Session],
) -> None:
    """A scheduler should skip a due trigger claimed by another scheduler."""

    workflow_definition = _create_workflow_definition(session)

    first_trigger = _create_trigger_definition(
        session,
        workflow_definition_id=workflow_definition.id,
    )
    second_trigger = _create_trigger_definition(
        session,
        workflow_definition_id=workflow_definition.id,
    )

    now = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    first_next_run_at = now - timedelta(minutes=2)
    second_next_run_at = now - timedelta(minutes=1)

    repository = ChronologicalTriggerRepository(session)

    repository.create(
        first_trigger.id,
        first_next_run_at,
    )
    repository.create(
        second_trigger.id,
        second_next_run_at,
    )

    # Make the setup visible to independent database sessions.
    session.commit()

    session_a = session_factory()
    session_b = session_factory()

    try:
        repository_a = ChronologicalTriggerRepository(session_a)
        repository_b = ChronologicalTriggerRepository(session_b)

        # Scheduler A claims the earliest trigger and keeps its transaction
        # open, retaining the FOR UPDATE lock.
        claimed_by_a = repository_a.get_next_due(now)

        assert claimed_by_a is not None
        assert claimed_by_a.trigger_definition_id == first_trigger.id

        # Scheduler B must skip A's locked row and claim the next due trigger.
        claimed_by_b = repository_b.get_next_due(now)

        assert claimed_by_b is not None
        assert claimed_by_b.trigger_definition_id == second_trigger.id

        # Each scheduler can independently advance the trigger it claimed.
        repository_a.update_next_run(
            claimed_by_a.trigger_definition_id,
            now + timedelta(minutes=1),
        )
        repository_b.update_next_run(
            claimed_by_b.trigger_definition_id,
            now + timedelta(minutes=2),
        )

        session_a.commit()
        session_b.commit()

    finally:
        session_a.rollback()
        session_b.rollback()
        session_a.close()
        session_b.close()

    # Verify both independent updates were persisted.
    session.expire_all()

    first_state = session.get(
        ChronologicalTriggerStateModel,
        first_trigger.id,
    )
    second_state = session.get(
        ChronologicalTriggerStateModel,
        second_trigger.id,
    )

    assert first_state is not None
    assert second_state is not None
    assert first_state.next_run_at == now + timedelta(minutes=1)
    assert second_state.next_run_at == now + timedelta(minutes=2)


def test_get_next_due_returns_none_when_only_due_trigger_is_locked(
    session: Session,
    session_factory: sessionmaker[Session],
) -> None:
    """A scheduler should not claim a due trigger held by another scheduler."""

    workflow_definition = _create_workflow_definition(session)

    trigger_definition = _create_trigger_definition(
        session,
        workflow_definition_id=workflow_definition.id,
    )

    now = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)

    repository = ChronologicalTriggerRepository(session)

    repository.create(
        trigger_definition.id,
        now - timedelta(minutes=1),
    )

    # Independent sessions cannot see uncommitted setup data.
    session.commit()

    session_a = session_factory()
    session_b = session_factory()

    try:
        repository_a = ChronologicalTriggerRepository(session_a)
        repository_b = ChronologicalTriggerRepository(session_b)

        # Scheduler A claims the only due trigger and keeps the transaction
        # open so its row remains locked.
        claimed_by_a = repository_a.get_next_due(now)

        assert claimed_by_a is not None
        assert claimed_by_a.trigger_definition_id == trigger_definition.id

        # Scheduler B must skip the locked row rather than returning the
        # same trigger or waiting for scheduler A.
        claimed_by_b = repository_b.get_next_due(now)

        assert claimed_by_b is None

    finally:
        session_a.rollback()
        session_b.rollback()
        session_a.close()
        session_b.close()
