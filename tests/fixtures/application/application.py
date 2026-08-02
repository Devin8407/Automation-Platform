from unittest.mock import MagicMock

import pytest

from automation_platform.application import WorkflowDefinitionService, WorkflowStartService


@pytest.fixture
def mock_task_registry():
    """Create a mocked task registry."""

    return MagicMock()


@pytest.fixture
def mock_trigger_registry():
    """Create a mocked trigger registry."""

    return MagicMock()


@pytest.fixture
def mock_execution_queue():
    """Create a mocked execution queue."""

    return MagicMock()


@pytest.fixture
def mock_uow():
    """Create a mocked uow."""

    uow = MagicMock()
    uow.__enter__.return_value = uow
    uow.__exit__.return_value = None

    return uow


@pytest.fixture
def mock_uow_factory(mock_uow):
    """Create a mocked uow factory."""

    factory = MagicMock(return_value=mock_uow)

    return factory


@pytest.fixture
def mock_workflow_definitions_service(
    mock_uow_factory,
    mock_task_registry,
    mock_trigger_registry,
) -> WorkflowStartService:
    """Create a workflow definitions service with mocked dependencies."""

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
    """Create a workflow start service with mocked dependencies."""

    return WorkflowStartService(
        uow_factory=mock_uow_factory,
        execution_queue=mock_execution_queue,
    )
