from collections.abc import Callable
from unittest.mock import MagicMock

import pytest

from automation_platform.application.workflow_definitions.models import (
    CreateTaskDefinition,
    CreateTriggerDefinition,
    CreateWorkflowDefinition,
)


@pytest.fixture
def create_task_definition_factory() -> Callable[..., CreateTaskDefinition]:
    def factory(
        *,
        plugin_type: str = "test_task",
        key: str = "task_a",
        configuration=None,
        dependencies=None,
        max_retries: int = 0,
    ) -> CreateTaskDefinition:
        return CreateTaskDefinition(
            plugin_type=plugin_type,
            key=key,
            configuration=configuration if configuration is not None else {},
            dependencies=dependencies if dependencies is not None else [],
            max_retries=max_retries,
        )

    return factory


@pytest.fixture
def create_trigger_definition_factory() -> Callable[..., CreateTriggerDefinition]:
    def factory(
        *,
        plugin_type: str = "test_trigger",
        configuration=None,
        enabled: bool = True,
    ) -> CreateTriggerDefinition:
        return CreateTriggerDefinition(
            plugin_type=plugin_type,
            configuration=configuration if configuration is not None else {},
            enabled=enabled,
        )

    return factory


@pytest.fixture
def create_workflow_definition_factory(
    create_task_definition_factory: Callable[..., CreateTaskDefinition],
    create_trigger_definition_factory: Callable[..., CreateTriggerDefinition],
) -> Callable[..., CreateWorkflowDefinition]:
    def factory(
        *,
        name: str = "Test Workflow",
        description: str = "Test workflow description",
        tasks: list[CreateTaskDefinition] = None,
        triggers: list[CreateTriggerDefinition] = None,
        enabled: bool = True,
    ) -> CreateWorkflowDefinition:
        return CreateWorkflowDefinition(
            name=name,
            description=description,
            tasks=tasks if tasks is not None else [create_task_definition_factory()],
            triggers=triggers if triggers is not None else [create_trigger_definition_factory()],
            enabled=enabled,
        )

    return factory


@pytest.fixture
def mock_task_registry():
    return MagicMock()


@pytest.fixture
def mock_trigger_registry():
    return MagicMock()


@pytest.fixture
def mock_uow():
    uow = MagicMock()
    uow.__enter__.return_value = uow
    uow.__exit__.return_value = None
    return uow


@pytest.fixture
def mock_uow_factory(mock_uow):
    factory = MagicMock(return_value=mock_uow)
    return factory
