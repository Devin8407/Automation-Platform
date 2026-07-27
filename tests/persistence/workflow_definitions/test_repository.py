"""
Tests for the workflow definition repository.
"""

from uuid import uuid4

from sqlalchemy.orm import Session

from automation_platform.persistence.workflow_definitions import (
    WorkflowDefinitionRepository,
)


def test_load_returns_none_when_workflow_does_not_exist(
    session: Session,
) -> None:
    """Loading an unknown workflow returns None."""

    repository = WorkflowDefinitionRepository(session)

    assert repository.load(uuid4()) is None


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

    first = task_definition_factory(key="extract")

    second = task_definition_factory(key="transform", dependencies=[first.id])

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


def test_save_updates_existing_workflow(session: Session, workflow_definition_factory) -> None:
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


def test_save_and_load_empty_workflow(session: Session, workflow_definition_factory) -> None:
    """Workflows without tasks or triggers round-trip through persistence."""

    workflow = workflow_definition_factory(task_definitions=[], trigger_definitions=[])

    repository = WorkflowDefinitionRepository(session)

    repository.save(workflow)
    session.commit()

    loaded = repository.load(workflow.id)

    assert loaded == workflow


def test_update_existing_workflow_definition(session: Session, workflow_definition_factory) -> None:
    """Existing workflow definitions can be updated."""

    workflow = workflow_definition_factory(
        name="Original",
        description="Original description",
        enabled=True,
    )

    repository = WorkflowDefinitionRepository(session)

    repository.save(workflow)
    session.commit()

    workflow.name = "Updated"
    workflow.description = "Updated description"
    workflow.enabled = False

    repository.save(workflow)
    session.commit()

    loaded = repository.load(workflow.id)

    assert loaded == workflow


def test_update_task_dependencies(
    session: Session,
    workflow_definition_factory,
    task_definition_factory,
) -> None:
    """Task dependency changes replace previous dependency relationships."""

    first = task_definition_factory(key="extract")

    second = task_definition_factory(key="transform", dependencies=[first.id])

    workflow = workflow_definition_factory(
        task_definitions=[
            first,
            second,
        ],
    )

    repository = WorkflowDefinitionRepository(session)

    repository.save(workflow)
    session.commit()

    second.dependencies = []

    repository.save(workflow)
    session.commit()

    loaded = repository.load(workflow.id)

    assert loaded == workflow


def test_save_and_load_complex_task_dependencies(
    session: Session,
    workflow_definition_factory,
    task_definition_factory,
) -> None:
    """Complex dependency graphs survive persistence."""

    extract = task_definition_factory(key="extract")

    validate = task_definition_factory(key="validate", dependencies=[extract.id])

    transform = task_definition_factory(key="transform", dependencies=[extract.id])

    load = task_definition_factory(
        key="load",
        dependencies=[
            validate.id,
            transform.id,
        ],
    )

    workflow = workflow_definition_factory(
        task_definitions=[
            extract,
            validate,
            transform,
            load,
        ],
    )

    repository = WorkflowDefinitionRepository(session)

    repository.save(workflow)
    session.commit()

    loaded = repository.load(workflow.id)

    assert loaded == workflow


def test_remove_task_definition(
    session: Session,
    workflow_definition_factory,
    task_definition_factory,
) -> None:
    """Removing a task definition removes it from persistence."""

    first = task_definition_factory(key="extract")
    second = task_definition_factory(key="transform")

    workflow = workflow_definition_factory(
        task_definitions=[first, second],
    )

    repository = WorkflowDefinitionRepository(session)

    repository.save(workflow)
    session.commit()

    workflow.task_definitions.remove(second)

    repository.save(workflow)
    session.commit()

    loaded = repository.load(workflow.id)

    assert loaded == workflow


def test_remove_trigger_definition(
    session: Session,
    workflow_definition_factory,
    trigger_definition_factory,
) -> None:
    """Removing a trigger removes it from persistence."""

    first = trigger_definition_factory(plugin_type="first")
    second = trigger_definition_factory(plugin_type="second")

    workflow = workflow_definition_factory(
        trigger_definitions=[first, second],
    )

    repository = WorkflowDefinitionRepository(session)

    repository.save(workflow)
    session.commit()

    workflow.trigger_definitions.remove(second)

    repository.save(workflow)
    session.commit()

    loaded = repository.load(workflow.id)

    assert loaded == workflow


def test_update_task_definition(
    session: Session,
    workflow_definition_factory,
    task_definition_factory,
) -> None:
    """Task definition updates are persisted."""

    task = task_definition_factory(
        key="extract",
        plugin_type="plugin.old",
        max_retries=3,
    )

    workflow = workflow_definition_factory(
        task_definitions=[task],
    )

    repository = WorkflowDefinitionRepository(session)

    repository.save(workflow)
    session.commit()

    task.plugin_type = "plugin.new"
    task.max_retries = 10

    repository.save(workflow)
    session.commit()

    loaded = repository.load(workflow.id)

    assert loaded == workflow


def test_update_trigger_definition(
    session: Session,
    workflow_definition_factory,
    trigger_definition_factory,
) -> None:
    """Trigger definition updates are persisted."""

    trigger = trigger_definition_factory(
        plugin_type="trigger.old",
        enabled=True,
    )

    workflow = workflow_definition_factory(
        trigger_definitions=[trigger],
    )

    repository = WorkflowDefinitionRepository(session)

    repository.save(workflow)
    session.commit()

    trigger.plugin_type = "trigger.new"
    trigger.enabled = False

    repository.save(workflow)
    session.commit()

    loaded = repository.load(workflow.id)

    assert loaded == workflow
