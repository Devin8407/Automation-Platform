"""Tests for the workflow definition application service."""

from unittest.mock import MagicMock
from uuid import UUID

import pytest

from automation_platform.application import (
    InvalidWorkflowDefinitionError,
    WorkflowDefinitionService,
)
from automation_platform.domain import WorkflowDefinition
from automation_platform.plugins import InvalidPluginConfigurationError

# ==================================================================================================
# Helpers
# ==================================================================================================


def configure_plugin_registry(registry: MagicMock, valid_types: set[str]) -> None:
    """Configure a mock plugin registry with the given available plugin types."""

    registry.contains.side_effect = lambda plugin_type: plugin_type in valid_types

    plugin = MagicMock()
    plugin.validate_configuration.return_value = None
    registry.get.return_value = plugin


# ==================================================================================================
# Fixtures
# ==================================================================================================


@pytest.fixture
def service(
    mock_uow_factory,
    mock_task_registry,
    mock_trigger_registry,
) -> WorkflowDefinitionService:
    """Create a workflow definition service with mocked dependencies."""

    configure_plugin_registry(mock_task_registry, {"test_task"})
    configure_plugin_registry(mock_trigger_registry, {"test_trigger"})

    return WorkflowDefinitionService(
        uow_factory=mock_uow_factory,
        task_registry=mock_task_registry,
        trigger_registry=mock_trigger_registry,
    )


# ==================================================================================================
# Create
# ==================================================================================================


def test_create_persists_workflow_definition(
    service,
    create_workflow_definition_factory,
    mock_uow,
):
    """Creating a valid workflow should persist the complete definition."""

    request = create_workflow_definition_factory(
        name="Example Workflow",
        description="Example description",
        enabled=False,
    )

    workflow_definition_id = service.create(request)

    mock_uow.workflow_definitions.save.assert_called_once()

    saved_workflow = mock_uow.workflow_definitions.save.call_args.args[0]

    assert isinstance(saved_workflow, WorkflowDefinition)
    assert saved_workflow.id == workflow_definition_id
    assert isinstance(workflow_definition_id, UUID)

    assert saved_workflow.name == "Example Workflow"
    assert saved_workflow.description == "Example description"
    assert saved_workflow.enabled is False

    assert len(saved_workflow.task_definitions) == 1
    assert len(saved_workflow.trigger_definitions) == 1

    mock_uow.commit.assert_called_once_with()


def test_create_constructs_task_definitions(
    service,
    create_task_definition_factory,
    create_workflow_definition_factory,
    mock_uow,
):
    """Creating a workflow should construct its task definitions correctly."""

    request = create_workflow_definition_factory(
        tasks=[
            create_task_definition_factory(
                plugin_type="test_task",
                key="task_a",
                configuration={"value": 1},
                max_tries=3,
            )
        ]
    )

    service.create(request)

    saved_workflow = mock_uow.workflow_definitions.save.call_args.args[0]
    task = saved_workflow.task_definitions[0]

    assert task.plugin_type == "test_task"
    assert task.key == "task_a"
    assert task.configuration == {"value": 1}
    assert task.dependencies == []
    assert task.max_tries == 3


def test_create_resolves_dependency_keys_to_ids(
    service,
    create_task_definition_factory,
    create_workflow_definition_factory,
    mock_uow,
):
    """Task dependency keys should be resolved to task definition identifiers."""

    request = create_workflow_definition_factory(
        tasks=[
            create_task_definition_factory(
                key="task_a",
            ),
            create_task_definition_factory(
                key="task_b",
                dependencies=["task_a"],
            ),
            create_task_definition_factory(
                key="task_c",
                dependencies=["task_a", "task_b"],
            ),
        ]
    )

    service.create(request)

    saved_workflow = mock_uow.workflow_definitions.save.call_args.args[0]

    tasks = {task.key: task for task in saved_workflow.task_definitions}

    assert tasks["task_a"].dependencies == []
    assert tasks["task_b"].dependencies == [tasks["task_a"].id]
    assert tasks["task_c"].dependencies == [
        tasks["task_a"].id,
        tasks["task_b"].id,
    ]


def test_create_constructs_trigger_definitions(
    service,
    create_trigger_definition_factory,
    create_workflow_definition_factory,
    mock_uow,
):
    """Creating a workflow should construct its trigger definitions correctly."""

    request = create_workflow_definition_factory(
        triggers=[
            create_trigger_definition_factory(
                plugin_type="test_trigger",
                configuration={"value": 1},
                enabled=False,
            )
        ]
    )

    service.create(request)

    saved_workflow = mock_uow.workflow_definitions.save.call_args.args[0]
    trigger = saved_workflow.trigger_definitions[0]

    assert trigger.plugin_type == "test_trigger"
    assert trigger.configuration == {"value": 1}
    assert trigger.enabled is False


def test_create_rejects_no_tasks(
    service,
    create_task_definition_factory,
    create_workflow_definition_factory,
):
    """Creating a workflow should reject if no tasks."""

    request = create_workflow_definition_factory(tasks=[])

    with pytest.raises(InvalidWorkflowDefinitionError):
        service.create(request)


def test_create_rejects_unknown_task_plugin(
    service,
    create_task_definition_factory,
    create_workflow_definition_factory,
):
    """Creating a workflow should reject an unknown task plugin."""

    request = create_workflow_definition_factory(
        tasks=[
            create_task_definition_factory(
                plugin_type="unknown_task",
            )
        ]
    )

    with pytest.raises(InvalidWorkflowDefinitionError):
        service.create(request)


def test_create_rejects_unknown_trigger_plugin(
    service,
    create_trigger_definition_factory,
    create_workflow_definition_factory,
):
    """Creating a workflow should reject an unknown trigger plugin."""

    request = create_workflow_definition_factory(
        triggers=[
            create_trigger_definition_factory(
                plugin_type="unknown_trigger",
            )
        ]
    )

    with pytest.raises(InvalidWorkflowDefinitionError):
        service.create(request)


def test_create_rejects_duplicate_task_keys(
    service,
    create_task_definition_factory,
    create_workflow_definition_factory,
):
    """Creating a workflow should reject duplicate task keys."""

    request = create_workflow_definition_factory(
        tasks=[
            create_task_definition_factory(key="duplicate"),
            create_task_definition_factory(key="duplicate"),
        ]
    )

    with pytest.raises(InvalidWorkflowDefinitionError):
        service.create(request)


def test_create_rejects_duplicate_dependencies(
    service,
    create_task_definition_factory,
    create_workflow_definition_factory,
):
    """Creating a workflow should reject duplicate task dependencies."""

    request = create_workflow_definition_factory(
        tasks=[
            create_task_definition_factory(key="task_a"),
            create_task_definition_factory(
                key="task_b",
                dependencies=["task_a", "task_a"],
            ),
        ]
    )

    with pytest.raises(InvalidWorkflowDefinitionError):
        service.create(request)


def test_create_rejects_self_dependency(
    service,
    create_task_definition_factory,
    create_workflow_definition_factory,
):
    """Creating a workflow should reject a task that depends on itself."""

    request = create_workflow_definition_factory(
        tasks=[
            create_task_definition_factory(
                key="task_a",
                dependencies=["task_a"],
            )
        ]
    )

    with pytest.raises(InvalidWorkflowDefinitionError):
        service.create(request)


def test_create_rejects_unknown_dependency(
    service,
    create_task_definition_factory,
    create_workflow_definition_factory,
):
    """Creating a workflow should reject references to nonexistent tasks."""

    request = create_workflow_definition_factory(
        tasks=[
            create_task_definition_factory(
                key="task_a",
                dependencies=["missing_task"],
            )
        ]
    )

    with pytest.raises(InvalidWorkflowDefinitionError):
        service.create(request)


def test_create_rejects_no_max_tries(
    service,
    create_task_definition_factory,
    create_workflow_definition_factory,
):
    """Creating a workflow should reject max_tries < 1."""

    request = create_workflow_definition_factory(
        tasks=[
            create_task_definition_factory(
                key="task_a",
                max_tries=0,
            )
        ]
    )

    with pytest.raises(InvalidWorkflowDefinitionError):
        service.create(request)


def test_create_rejects_dependency_cycle(
    service,
    create_task_definition_factory,
    create_workflow_definition_factory,
):
    """Creating a workflow should reject cyclic task dependencies."""

    request = create_workflow_definition_factory(
        tasks=[
            create_task_definition_factory(
                key="task_a",
                dependencies=["task_c"],
            ),
            create_task_definition_factory(
                key="task_b",
                dependencies=["task_a"],
            ),
            create_task_definition_factory(
                key="task_c",
                dependencies=["task_b"],
            ),
        ]
    )

    with pytest.raises(InvalidWorkflowDefinitionError):
        service.create(request)


def test_create_accepts_nontrivial_acyclic_graph(
    service,
    create_task_definition_factory,
    create_workflow_definition_factory,
    mock_uow,
):
    """Creating a workflow should accept a valid branching dependency graph."""

    request = create_workflow_definition_factory(
        tasks=[
            create_task_definition_factory(key="task_a"),
            create_task_definition_factory(key="task_b"),
            create_task_definition_factory(
                key="task_c",
                dependencies=["task_a", "task_b"],
            ),
            create_task_definition_factory(
                key="task_d",
                dependencies=["task_b"],
            ),
            create_task_definition_factory(
                key="task_e",
                dependencies=["task_c", "task_d"],
            ),
        ]
    )

    service.create(request)

    mock_uow.workflow_definitions.save.assert_called_once()
    mock_uow.commit.assert_called_once_with()


def test_create_rejects_invalid_task_configuration(
    service,
    create_task_definition_factory,
    create_workflow_definition_factory,
    mock_task_registry,
):
    plugin = mock_task_registry.get.return_value
    plugin.validate_configuration.side_effect = InvalidPluginConfigurationError(
        "Invalid configuration."
    )

    request = create_workflow_definition_factory(
        tasks=[
            create_task_definition_factory(
                key="task_a",
                configuration={"invalid": True},
            )
        ]
    )

    with pytest.raises(
        InvalidWorkflowDefinitionError,
        match="Invalid configuration for task 'task_a'",
    ):
        service.create(request)


def test_create_validates_trigger_configuration_with_trigger_registry(
    service,
    create_trigger_definition_factory,
    create_workflow_definition_factory,
    mock_trigger_registry,
):
    request = create_workflow_definition_factory(
        triggers=[
            create_trigger_definition_factory(
                plugin_type="test_trigger",
                configuration={"value": 1},
            )
        ]
    )

    service.create(request)

    mock_trigger_registry.get.assert_called_once_with("test_trigger")
    mock_trigger_registry.get.return_value.validate_configuration.assert_called_once_with(
        {"value": 1}
    )


def test_create_rejects_invalid_trigger_configuration(
    service,
    create_trigger_definition_factory,
    create_workflow_definition_factory,
    mock_trigger_registry,
):
    plugin = mock_trigger_registry.get.return_value
    plugin.validate_configuration.side_effect = InvalidPluginConfigurationError(
        "Invalid configuration."
    )

    request = create_workflow_definition_factory(
        triggers=[
            create_trigger_definition_factory(
                configuration={"invalid": True},
            )
        ]
    )

    with pytest.raises(
        InvalidWorkflowDefinitionError,
        match="Invalid configuration for trigger",
    ):
        service.create(request)


# ==================================================================================================
# Delete
# ==================================================================================================


def test_delete_deletes_workflow_definition(
    service,
    mock_uow,
):
    """Deleting a workflow should delete the requested definition and commit."""

    workflow_definition_id = UUID("12345678-1234-5678-1234-567812345678")

    service.delete(workflow_definition_id)

    mock_uow.workflow_definitions.delete.assert_called_once_with(workflow_definition_id)
    mock_uow.commit.assert_called_once_with()
