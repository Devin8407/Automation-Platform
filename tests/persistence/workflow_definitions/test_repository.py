"""
Tests for the workflow definition repository.
"""

from sqlalchemy.orm import Session

from automation_platform.domain.workflow_definitions import WorkflowDefinition
from automation_platform.persistence.workflow_definitions import (
    WorkflowDefinitionRepository,
)


def test_load_returns_none_when_workflow_does_not_exist(
    session: Session,
) -> None:
    """Loading an unknown workflow returns None."""

    repository = WorkflowDefinitionRepository(session)

    assert repository.load(WorkflowDefinition.new_id()) is None


def test_save_and_load_workflow(
    session: Session,
    workflow_definition_factory,
) -> None:
    """A saved workflow can be loaded again."""

    workflow = workflow_definition_factory()

    repository = WorkflowDefinitionRepository(session)

    repository.save(workflow)
    session.commit()

    loaded = repository.load(workflow.id)

    assert loaded == workflow


def test_delete_workflow(
    session: Session,
    workflow_definition_factory,
) -> None:
    """Deleting a workflow removes it from persistence."""

    workflow = workflow_definition_factory()

    repository = WorkflowDefinitionRepository(session)

    repository.save(workflow)
    session.commit()

    repository.delete(workflow.id)
    session.commit()

    assert repository.load(workflow.id) is None


def test_save_and_load_workflow_with_multiple_tasks(
    session: Session,
    workflow_definition_factory,
    task_definition_factory,
) -> None:
    """Tasks are persisted with their owning workflow."""

    task_one = task_definition_factory(key="extract")
    task_two = task_definition_factory(key="transform")
    task_three = task_definition_factory(key="load")

    workflow = workflow_definition_factory(
        task_definitions=[
            task_one,
            task_two,
            task_three,
        ],
    )

    repository = WorkflowDefinitionRepository(session)

    repository.save(workflow)
    session.commit()

    loaded = repository.load(workflow.id)

    assert loaded == workflow


def test_save_and_load_workflow_with_triggers(
    session: Session,
    workflow_definition_factory,
    trigger_definition_factory,
) -> None:
    """Triggers are persisted with their owning workflow."""

    cron = trigger_definition_factory(
        plugin_type="cron",
    )

    webhook = trigger_definition_factory(
        plugin_type="webhook",
    )

    workflow = workflow_definition_factory(
        trigger_definitions=[
            cron,
            webhook,
        ],
    )

    repository = WorkflowDefinitionRepository(session)

    repository.save(workflow)
    session.commit()

    loaded = repository.load(workflow.id)

    assert loaded == workflow


def test_save_and_load_task_dependencies(
    session: Session,
    workflow_definition_factory,
    task_definition_factory,
) -> None:
    """Task dependency relationships are preserved."""

    first = task_definition_factory(
        key="extract",
    )

    second = task_definition_factory(
        key="transform",
        dependencies=[first.id],
    )

    third = task_definition_factory(
        key="load",
        dependencies=[
            first.id,
            second.id,
        ],
    )

    workflow = workflow_definition_factory(
        task_definitions=[
            first,
            second,
            third,
        ],
    )

    repository = WorkflowDefinitionRepository(session)

    repository.save(workflow)
    session.commit()

    loaded = repository.load(workflow.id)

    assert loaded == workflow


def test_save_updates_existing_workflow(
    session: Session,
    workflow_definition_factory,
) -> None:
    """Saving an existing workflow updates its persisted state."""

    workflow = workflow_definition_factory()

    repository = WorkflowDefinitionRepository(session)

    repository.save(workflow)
    session.commit()

    workflow.name = "Updated Workflow"

    repository.save(workflow)
    session.commit()

    loaded = repository.load(workflow.id)

    assert loaded == workflow
