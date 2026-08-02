"""Mock fixtures for application service tests."""

from unittest.mock import MagicMock

import pytest

from automation_platform.application import (
    TaskProcessingService,
    WorkflowDefinitionService,
    WorkflowStartService,
)


@pytest.fixture
def mock_task_plugin():
    """Return a mocked task plugin instance."""

    return MagicMock()


@pytest.fixture
def mock_task_plugin_type(mock_task_plugin):
    """Return a mocked task plugin implementation class."""

    return MagicMock(return_value=mock_task_plugin)


@pytest.fixture
def mock_task_registry(mock_task_plugin_type):
    """Return a mocked task plugin registry."""

    registry = MagicMock()
    registry.get.return_value = mock_task_plugin_type

    return registry


@pytest.fixture
def mock_trigger_plugin():
    """Return a mocked trigger plugin instance."""

    return MagicMock()


@pytest.fixture
def mock_trigger_plugin_type(mock_trigger_plugin):
    """Return a mocked trigger plugin implementation class."""

    return MagicMock(return_value=mock_trigger_plugin)


@pytest.fixture
def mock_trigger_registry(mock_trigger_plugin_type):
    """Return a mocked trigger plugin registry."""

    registry = MagicMock()
    registry.get.return_value = mock_trigger_plugin_type

    return registry


@pytest.fixture
def mock_execution_queue():
    """Return a mocked execution queue."""

    return MagicMock()


@pytest.fixture
def mock_uow():
    """Return a mocked unit of work."""

    uow = MagicMock()
    uow.__enter__.return_value = uow
    uow.__exit__.return_value = None

    return uow


@pytest.fixture
def mock_uow_factory(mock_uow):
    """Return a mocked unit-of-work factory."""

    return MagicMock(return_value=mock_uow)


@pytest.fixture
def mock_workflow_definitions_service(
    mock_uow_factory,
    mock_task_registry,
    mock_trigger_registry,
) -> WorkflowDefinitionService:
    """Return a workflow definition service with mocked dependencies."""

    return WorkflowDefinitionService(
        uow_factory=mock_uow_factory,
        task_registry=mock_task_registry,
        trigger_registry=mock_trigger_registry,
    )


@pytest.fixture
def mock_workflow_start_service(
    mock_uow_factory,
    mock_execution_queue,
) -> WorkflowStartService:
    """Return a workflow start service with mocked dependencies."""

    return WorkflowStartService(
        uow_factory=mock_uow_factory,
        execution_queue=mock_execution_queue,
    )


@pytest.fixture
def mock_task_processing_service(
    mock_uow_factory,
    mock_task_registry,
) -> TaskProcessingService:
    """Return a task processing service with mocked dependencies."""

    return TaskProcessingService(
        uow_factory=mock_uow_factory,
        task_registry=mock_task_registry,
    )
